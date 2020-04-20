from functools import partial
import time
from threading import Thread, Event
from typing import List
from queue import Queue
import json

from graphql_client import GraphQLClient


TEST_SUBSCRIPTION_URL = "ws://localhost:8000/subscriptions"


class Count:
    def __init__(self, flag: Event):
        self.count = 0
        self.flag = flag

    def increment(self):
        if self.flag.is_set() is True:
            self.count += 1


def test_subscription_rate(queries: [str], recording_time: float, result_queue: Queue):
    # This work around appears to be necessary so a reference can be passed to the callback
    # Create a Count instance for each subscription to avoid race conditions
    # Create a single Flag instance which is only read from the subscription threads and callbacks
    counting_flag = Event()
    messages_recieved = [Count(counting_flag) for q in queries]

    def message_callback(_id: any, data: any, message_counter: int = 0):
        messages_recieved[message_counter].increment()

    # Set up connection
    ws = GraphQLClient(TEST_SUBSCRIPTION_URL)

    start_time = time.time()

    # Set up the callbacks and add subscriptions
    subscription_ids = []
    for q_num in range(len(queries)):
        subscription_ids.append(
            ws.add_subscription(
                queries[q_num],
                callback=partial(message_callback, message_counter=q_num),
            )
        )

    counting_flag.set()

    time.sleep(recording_time)

    counting_flag.clear()

    # Close connections
    for sub_id in subscription_ids:
        ws.stop_subscribe(sub_id)
    ws.close()
    # Return the message rate
    # print(f"Messages: {[counter.count for counter in messages_recieved]}")
    total_messages_recieved = sum([counter.count for counter in messages_recieved])
    print(f"Total Messages: {total_messages_recieved}")
    result_queue.put((total_messages_recieved / len(queries)) / recording_time)


def measure_sine_subscription(
    subscriptions: int = 10, recording_time: int = 10, update_time: float = 0.1
) -> float:

    print("--- sim://sine ---")
    print(
        f"--- Subscriptions: {subscriptions}, Recording Time: {recording_time} s, Update Time: {update_time} s ---"
    )

    result_queue = Queue()

    sine_subscription = f"""subscription {{
  subscribeChannel(id: "sim://sine(-5,5,5,{update_time})") {{
    id
    value
  }}
}}
"""

    x = Thread(
        target=test_subscription_rate,
        args=([sine_subscription] * subscriptions, recording_time, result_queue),
    )
    x.start()
    x.join()
    result = result_queue.get()
    print(f"Recorded rate: {result:4f} Hz")

    return result


def measure_sinewave_subscription(
    subscriptions: int = 10,
    size: int = 1,
    recording_time: int = 10,
    update_time: float = 0.1,
) -> float:

    print("--- sim://sinewavesimple ---")
    print(
        f"--- Subscriptions: {subscriptions}, Size: {size}, Recording Time: {recording_time} s, Update Time: {update_time} s ---"
    )

    result_queue = Queue()

    sinewave_subscription = f"""subscription {{
  subscribeChannel(id: "sim://sinewavesimple({size},{update_time})") {{
    id
    value
  }}
}}
"""

    x = Thread(
        target=test_subscription_rate,
        args=([sinewave_subscription] * subscriptions, recording_time, result_queue),
    )
    x.start()
    x.join()
    result = result_queue.get()
    print(f"Recorded rate: {result:4f} Hz")

    return result


if __name__ == "__main__":

    subscription_numbers = (
        [10 * x for x in range(1, 10)]
        + [100 * x for x in range(1, 10)]
        + [1000 + (100 * x) for x in range(1, 11)]
    )

    results = {}

    for num in subscription_numbers:
        # results[num] = measure_sinewave_subscription(num, 100)
        results[num] = measure_sinewave_subscription(num, 10000)

    # with open("web_socket_results_sine.json", "w") as f:
    #     json.dump(results, f, indent=4)
