import argparse
import asyncio
import datetime
import json
import sys
import threading
import time

import psutil
import websockets

# Constants
cpu_average = 0
memory_use = 0
PV_PREFIX = "TEST:REC"
subscriptions_list = {}
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
    "--log",
    action="store_true",
    dest="log_progress",
    help="Indicate if client should log progress to tmp file",
)


class GraphQLClient:
    def __init__(self, endpoint, signal, ws_protocol, log_progress):
        self.endpoint = endpoint
        self.signal = signal
        self.ws_protocol = ws_protocol
        self.first_subscribe = True
        self.log = log_progress

        if self.log:
            print("Logging subscription progress")
            self.progress_file = open("/tmp/progress.txt", "w")

    async def subscribe(self, idid, query, handle, n_messages):
        monitor_progress = False
        if self.first_subscribe and self.log:
            monitor_progress = True
            self.first_subscribe = False
        connection_init_message = json.dumps({"type": "connection_init", "payload": {}})

        request_message_graphql_ws_protocol = json.dumps(
            {"type": "start", "id": idid, "payload": {"query": query}}
        )

        request_message_graphql_transport_ws_protocol = json.dumps(
            {"type": "subscribe", "id": idid, "payload": {"query": query}}
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
                data = json.loads(response)
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
                                if self.log:
                                    self.progress_file.close()
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
                                    self.progress_file.write(
                                        f"Collected {msg_count}/{n_messages} samples.\
                                            Remaining time: {round(remaining_time, 0)}\
                                            secs \n"
                                    )
                                    self.progress_file.flush()
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


async def coniql_subscription(client, pv_name, n_samples):
    subscriptions_list[pv_name] = PVSubscription(pv_name)
    await client.subscribe(
        idid=pv_name,
        query=get_subscription_query(pv_name),
        handle=data_handler,
        n_messages=n_samples,
    )


async def main():
    args = parser.parse_args()
    n_pvs = int(args.n_pvs)
    n_samples = int(args.n_samples)
    ws_protocol = int(args.ws_protocol)
    log_progress = args.log_progress

    protocol = "graphql-ws"
    if ws_protocol == 2:
        protocol = "graphql-transport-ws"
    print("-> Using the websocket protocol: '" + protocol + "'")

    # Create client
    signal = StartStopSignal()
    client = GraphQLClient(
        endpoint="ws://0.0.0.0:8080/ws",
        signal=signal,
        ws_protocol=ws_protocol,
        log_progress=log_progress,
    )
    # Start CPU monitor thread
    cpu_monitor_thread = threading.Thread(target=cpu_monitor, args=(signal,))
    cpu_monitor_thread.start()

    # Create subscription tasks for n_pvs
    for i in range(n_pvs):
        # Get the PV name
        pv_name = PV_PREFIX + str(i)

        # Create a task
        sub_task = asyncio.create_task(coniql_subscription(client, pv_name, n_samples))

        # Add to list of tasks to await
        task_list.append(sub_task)
        print("-> Starting subscription: " + str(pv_name))

    # Signal for the CPU monitor thread to start recording CPU metrics
    signal.signal_start()

    # Await all subscriptions to complete
    try:
        await asyncio.gather(*task_list)
        # Signal to CPU monitoring thread to stop recording CPU metrics
        signal.signal_stop()
    except Exception as e:
        # Catch any exceptions so that we can still record results
        print("Exception caught: ", e)

    # Analyse results
    missing_average = 0
    missing_max = 0
    for pv in subscriptions_list.keys():
        res = subscriptions_list[pv].get_values()
        if len(res) == 0:
            break
        expected_result = res[0]
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

    res_str = "[{}](nPVs={}, nsamples={}, protocol={})| Av. missed events: {}|\
 Max missed events: {}| CPU av.: {:.2f} %| Mem usage: {:.2f} MiB\n".format(
        datetime.datetime.now(),
        n_pvs,
        n_samples,
        protocol,
        round(missing_average),
        missing_max,
        cpu_average,
        memory_use,
    )
    with open(args.output_file, "a") as f:
        f.write(res_str)

    print("\n\n ****** SUMMARY ******")
    print(" Average missed events = " + str(round(missing_average)))
    print(" Max. missed events = " + str(missing_max))
    print(" CPU average: " + str(cpu_average) + " %")
    print(" Memory usage: " + str(memory_use) + " MiB")
    print(" *********************\n")
    sys.exit()


if __name__ == "__main__":
    asyncio.run(main())
    sys.exit()
