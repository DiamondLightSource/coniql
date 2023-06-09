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
thread_list = []

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


class GraphQLClient:
    def __init__(self, endpoint, signal, ws_protocol):
        self.endpoint = endpoint
        self.signal = signal
        self.ws_protocol = ws_protocol

    async def subscribe(self, idid, query, handle, n_messages):
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
                                break
                                print("break")
                            msg_count = msg_count + 1
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


def coniql_subscription(client, pv_name, n_samples):
    subscriptions_list[pv_name] = PVSubscription(pv_name)
    asyncio.run(
        client.subscribe(
            idid=pv_name,
            query=get_subscription_query(pv_name),
            handle=data_handler,
            n_messages=n_samples,
        )
    )


def main():
    args = parser.parse_args()
    n_pvs = int(args.n_pvs)
    n_samples = int(args.n_samples)
    ws_protocol = int(args.ws_protocol)

    protocol = "graphql-ws"
    if ws_protocol == 2:
        protocol = "graphql-transport-ws"
    print("-> Using the websocket protocol: '" + protocol + "'")

    # Create and start subscriptions
    signal = StartStopSignal()
    client = GraphQLClient(
        endpoint="ws://0.0.0.0:8080/ws", signal=signal, ws_protocol=ws_protocol
    )
    t = threading.Thread(target=cpu_monitor, args=(signal,))
    t.start()
    for i in range(n_pvs):
        # Get the PV name
        if i < 10:
            pv_name = PV_PREFIX + "0" + str(i)
        else:
            pv_name = PV_PREFIX + str(i)

        t = threading.Thread(
            target=coniql_subscription,
            args=(
                client,
                pv_name,
                n_samples,
            ),
        )
        thread_list.append(t)
        t.start()
        print("-> Starting subscription: " + str(pv_name))

    # Monitor subscription progress
    signal.signal_start()
    list_size_t0 = len(thread_list)
    while True:
        for thread in thread_list:
            if not thread.is_alive():
                thread_list.remove(thread)
                if len(thread_list) == list_size_t0 - 1:
                    print(
                        "-> Subscriptions starting to close at "
                        + str(datetime.datetime.now())
                    )
                    signal.signal_stop()
        if len(thread_list) == 0:
            print("-> All subscriptions completed at " + str(datetime.datetime.now()))
            break
        time.sleep(0.1)

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
    main()
    sys.exit()
