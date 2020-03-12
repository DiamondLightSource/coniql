from functools import partial
import time
from threading import Thread, Event
from typing import List
from queue import Queue

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


if __name__ == "__main__":
    result_queue = Queue()

    sine_subscription = """subscription {
  subscribeChannel(id: "sim://sine(-5,5,5,0.1)") {
    id
    value
  }
}
"""

    x = Thread(
        target=test_subscription_rate,
        args=([sine_subscription] * 100, 10, result_queue),
    )
    x.start()
    x.join()
    results = result_queue.get()
    print(f"Recorded rate: {results:4f} Hz")
