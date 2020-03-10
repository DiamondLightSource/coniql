import time
from threading import Thread
from queue import Queue

from graphql_client import GraphQLClient


TEST_SUBSCRIPTION_URL = "ws://localhost:8000/subscriptions"


def test_subscription_rate(query: str, recording_time: float, result_queue: Queue):
    messages_recieved = []

    def message_callback(_id, data, messages_recieved):
        messages_recieved.append(1)
        # print(messages_recieved)

    # Set up connection
    ws = GraphQLClient(TEST_SUBSCRIPTION_URL)
    # Set up the callback
    sub_id = ws.subscribe(
        query, callback=lambda x, y: message_callback(x, y, messages_recieved)
    )
    # Wait for set period of time
    time.sleep(recording_time)
    # Close connection
    ws.stop_subscribe(sub_id)
    ws.close()
    # Return the message rate
    result_queue.put(len(messages_recieved) / recording_time)


if __name__ == "__main__":
    result_queue = Queue()

    sine_subscription = """subscription {
  subscribeChannel(id: "sim://sine") {
    id
    value
  }
}
"""

    x = Thread(
        target=test_subscription_rate, args=(sine_subscription, 10, result_queue)
    )
    x.start()
    x.join()
    results = result_queue.get()
    print(f"Recorded rate: {results} Hz")
