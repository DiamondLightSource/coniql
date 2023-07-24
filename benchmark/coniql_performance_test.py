import argparse
import asyncio
import datetime
import sys
import threading
import time
import uuid
from typing import Dict

import ujson
import websockets

# Constants
cpu_average = 0
memory_use = 0
PV_PREFIX = "TEST:REC"
subscriptions_list: Dict[str, "PVSubscription"] = {}
task_list = []


parser = argparse.ArgumentParser(description="Process inputs")
parser.add_argument(
    "-n", "--npvs", action="store", dest="n_pvs", default=1, help="Number of PVs"
)
parser.add_argument(
    "-s",
    "--nsamples",
    action="store",
    dest="n_samples",
    default=10,
    help="Number of samples to collect",
)
parser.add_argument(
    "-p",
    "--protocol",
    action="store",
    dest="ws_protocol",
    choices=["1", "2"],
    default=1,
    help="websocket protocol: 1 = graphql-ws, 2 = graphql-transport-ws",
)
parser.add_argument(
    "-f",
    "--file",
    action="store",
    dest="output_file",
    default="performance_test_results.txt",
    help="File to output results to",
)
parser.add_argument(
    "-l",
    "--log-file",
    action="store",
    dest="log_filename",
    default=None,
    help="File to log subscription progress to",
)
parser.add_argument(
    "-x",
    "--no-cpu-monitor",
    action="store_true",
    dest="no_cpu_monitor",
    help="Do not run the CPU monitor",
)
parser.add_argument(
    "--coniql-addr",
    action="store",
    dest="addr",
    help="Address of Coniql server websocket",
    default="0.0.0.0:8080/ws",
)
parser.add_argument(
    "--debug", action="store_true", help="Enable extra debugging information"
)


class GraphQLClient:
    def __init__(self, endpoint, signal, ws_protocol, log_filename):
        self.endpoint = endpoint
        self.signal = signal
        self.ws_protocol = ws_protocol
        self.first_subscribe = True
        self.log_filename = log_filename

        if self.log_filename is not None:
            print("-> Logging subscription progress")
            self.log_file = open(self.log_filename, "w")
        else:
            self.log_file = None

    async def subscribe(self, idid, query, handle, n_messages, debug):
        monitor_progress = False
        if self.first_subscribe and self.log_filename is not None:
            monitor_progress = True
            self.first_subscribe = False

        if debug:
            monitor_progress = True

        uid = str(uuid.uuid4())
        connection_init_message = ujson.dumps(
            {"type": "connection_init", "payload": {}}
        )

        request_message_graphql_ws_protocol = ujson.dumps(
            {"type": "start", "id": uid, "payload": {"query": query}}
        )

        request_message_graphql_transport_ws_protocol = ujson.dumps(
            {"type": "subscribe", "id": uid, "payload": {"query": query}}
        )

        stop_message_graphql_ws_protocol = ujson.dumps({"type": "stop", "id": uid})

        stop_message_graphql_transport_ws_protocol = ujson.dumps(
            {"type": "complete", "id": uid}
        )

        protocols = ["graphql-ws", "graphql-transport-ws"]

        async with websockets.connect(
            self.endpoint,
            subprotocols=[protocols[self.ws_protocol - 1]],
        ) as websocket:
            await websocket.send(connection_init_message)
            if self.ws_protocol == 2:
                await websocket.send(request_message_graphql_transport_ws_protocol)
            else:
                await websocket.send(request_message_graphql_ws_protocol)

            msg_count = 0
            start_time = time.time()
            async for response in websocket:
                data = ujson.loads(response)
                if data["type"] == "connection_ack":
                    pass
                elif data["type"] == "ka":
                    pass
                else:
                    if self.signal.get_start():
                        handle(data["payload"])
                        if n_messages is None:
                            # Do nothing and continue subscription indefinitely
                            pass
                        else:
                            if msg_count > n_messages:
                                if self.ws_protocol == 2:
                                    await websocket.send(
                                        stop_message_graphql_ws_protocol
                                    )
                                else:
                                    await websocket.send(
                                        stop_message_graphql_transport_ws_protocol
                                    )

                                if self.log_file and not self.log_file.closed:
                                    self.log_file.close()
                                break
                            msg_count = msg_count + 1
                            if monitor_progress:
                                ten_percent = round(n_messages / 10, 0)
                                if msg_count % ten_percent == 0:
                                    remaining_time = (
                                        (time.time() - start_time)
                                        / msg_count
                                        * (n_messages - msg_count)
                                    )

                                    message = (
                                        f"Collected {msg_count}/{n_messages} samples "
                                        f"for pv {idid}. "
                                        f"Remaining time: {round(remaining_time, 0)}"
                                        "secs \n"
                                    )

                                    print(message)
                                    # The file may be closed by another instance of
                                    # this function.
                                    if self.log_file and not self.log_file.closed:
                                        self.log_file.write(message)
                                        self.log_file.flush()
                    else:
                        continue


class StartStopSignal:
    def __init__(self):
        self.start = False
        self.stop = False

    def signal_start(self):
        print("-> Starting monitor")
        self.start = True

    def signal_stop(self):
        print("-> Stopping monitor")
        self.stop = True

    def get_start(self):
        return self.start

    def get_stop(self):
        return self.stop


class PVSubscription:
    def __init__(self, pv):
        self.pv = pv
        self.values = []

    def append(self, value):
        self.values.append(value)

    def get_values(self):
        return self.values


def cpu_monitor(signal):
    # Keep import local so we don't need it in Container
    import psutil

    pid = 0
    for proc in psutil.process_iter(["pid", "name"]):
        if proc.info["name"] == "coniql":
            pid = proc.info["pid"]
            print("-> Monitoring PID: " + str(pid))

    p = psutil.Process(pid)
    mem = p.memory_info().rss / 1000000
    memi = mem
    cpu_res = []
    count = 0
    while True:
        if signal.get_stop():
            break
        if signal.get_start():
            cpu = p.cpu_percent(interval=1.0)
            mem = p.memory_info().rss / 1000000
            print("-> CPU: " + str(cpu) + ", MEM: " + str(mem))
            cpu_res.append(cpu)
            if count == 0:
                memi = mem
            count += 1
        time.sleep(0.1)

    memf = mem
    mem_use = memf - memi
    # Remove last element which may have been taken after subscriptions finished
    cpu_res.pop()
    if len(cpu_res) > 0:
        cpu_aver = sum(cpu_res) / (len(cpu_res))
        global cpu_average
        cpu_average = cpu_aver
        global memory_use
        memory_use = mem_use


def data_handler(data):
    id = data["data"]["subscribeChannel"]["id"]
    id = id.replace("ca://", "")

    # Add value to list
    value = data["data"]["subscribeChannel"]["value"]["float"]
    subscriptions_list[id].append(value)


def get_subscription_query(pv_name):
    return (
        """subscription {
  subscribeChannel(id: "ca://%s") {
    id
    time {
        datetime
    }
    value {
        string
        float
        base64Array {
          numberType
          base64
        }
      stringArray
      }
      status {
        quality
        message
        mutable
      }
      display {
        units
        form
        controlRange {
          max
          min
        }
        choices
        precision
      }
    }
  }"""
        % pv_name
    )


async def coniql_subscription(client: GraphQLClient, pv_name, n_samples, debug):
    subscriptions_list[pv_name] = PVSubscription(pv_name)
    await client.subscribe(
        idid=pv_name,
        query=get_subscription_query(pv_name),
        handle=data_handler,
        n_messages=n_samples,
        debug=debug,
    )


async def main():
    args = parser.parse_args()
    n_pvs = int(args.n_pvs)
    n_samples = int(args.n_samples)
    ws_protocol = int(args.ws_protocol)
    log_filename = args.log_filename
    no_cpu_monitor = args.no_cpu_monitor
    debug = args.debug

    protocol = "graphql-ws"
    if ws_protocol == 2:
        protocol = "graphql-transport-ws"
    print("-> Using the websocket protocol: '" + protocol + "'")

    # Create client
    signal = StartStopSignal()
    client = GraphQLClient(
        endpoint=f"ws://{args.addr}",
        signal=signal,
        ws_protocol=ws_protocol,
        log_filename=log_filename,
    )
    # Start CPU monitor thread
    if no_cpu_monitor:
        print("-> Not running CPU monitor")
    else:
        cpu_monitor_thread = threading.Thread(target=cpu_monitor, args=(signal,))
        cpu_monitor_thread.start()

    # Create subscription tasks for n_pvs
    for i in range(n_pvs):
        # Get the PV name
        pv_name = PV_PREFIX + str(i)

        # Create a task
        sub_task = asyncio.create_task(
            coniql_subscription(client, pv_name, n_samples, debug)
        )

        # Add to list of tasks to await
        task_list.append(sub_task)
        print("-> Starting subscription: " + str(pv_name))

    # Signal for the CPU monitor thread to start recording CPU metrics
    signal.signal_start()

    start_time = time.time()

    # Await all subscriptions to complete
    try:
        await asyncio.gather(*task_list)
        exit_code = 0
    except Exception as e:
        # Catch any exceptions so that we can still record results
        print("Exception caught: ", e)
        print("repr: ", repr(e))  # Sometimes just printing "e" is blank...
        exit_code = 1
    finally:
        # Signal to CPU monitoring thread to stop recording CPU metrics
        signal.signal_stop()

    duration = time.time() - start_time

    # Analyse results
    missing_average = 0
    missing_max = 0
    for pv in subscriptions_list.keys():
        res = subscriptions_list[pv].get_values()
        if len(res) == 0:
            break
        expected_result = res[0]

        if expected_result is None:
            print("ERROR: Found None for ", pv, " ", res)

        missing = 0
        for val in res:
            if val != expected_result:
                n_missed = val - expected_result
                missing = missing + n_missed
                expected_result = val + 1
            else:
                expected_result += 1

        if missing > missing_max:
            missing_max = missing
        missing_average = missing_average + missing / n_pvs
        sample_range = max(res) - min(res) + 1
        print(
            pv
            + " processing complete: value range "
            + str(sample_range)
            + ", missing "
            + str(missing)
        )

    # Collect results
    time.sleep(1)

    # NOTE: Kubernetes performance test relies on these being the last 3 lines
    # of output when not using CPU monitor
    print("\n\n ****** SUMMARY ******")
    print(" Average missed events = " + str(round(missing_average)))
    print(" Max. missed events = " + str(missing_max))

    if not no_cpu_monitor:
        res_str = (
            f"[{datetime.datetime.now()}](nPVs={n_pvs}, nsamples={n_samples}, "
            f"protocol={protocol})| Av. missed events: {round(missing_average)}| "
            f"Max missed events: {missing_max}| CPU av.: {cpu_average:.2f} %| "
            f"Mem usage: {memory_use:.2f} MiB| Duration: {duration:.2f} secs\n"
        )

        with open(args.output_file, "a") as f:
            f.write(res_str)

        print(" CPU average: " + str(cpu_average) + " %")
        print(" Memory usage: " + str(memory_use) + " MiB")
        print(" *********************\n")
    sys.exit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())
