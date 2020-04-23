import time

from graphql_client import GraphQLClient

TEST_SUBSCRIPTION_URL = "ws://localhost:8000/subscriptions"

def measure_sinewave_simple(
    size: int, update_time: float, measure_time: float
) -> float:

    print("--- sim://sinewavesimple ---")
    print(
        f"--- Size: {size}, Update Time: {update_time} s, Measurement Time: {measure_time} s, ---"
    )

    count = 0

    def add_count(x, y):
        nonlocal count
        # print(count)
        count += 1

    sinewave_subscription = f"""subscription {{
  subscribeChannel(id: "sim://sinewavesimple({size},{update_time})") {{
    id
    value
  }}
}}
"""

    # Set up connection
    ws = GraphQLClient(TEST_SUBSCRIPTION_URL)

    # Set up the callbacks and add subscription
    sub_id = ws.subscribe(query=sinewave_subscription, callback=add_count)

    start_time = time.time()

    time.sleep(measure_time)

    ws.stop_subscribe(sub_id)

    end_time = time.time()
    ws.close()

    recorded_time = end_time - start_time
    # Return the message rate
    # print(f"Messages: {[counter.count for counter in messages_recieved]}")
    print(f"Final count: {count}")
    print(f"Execution Time: {recorded_time} s")
    message_freq = count / recorded_time
    print(f"Measured Frequency: {message_freq} Hz")

    return message_freq

if __name__ == "__main__":
    results = []
    # results.append(measure_sinewave_simple(1, 0.1, 10))
    # results.append(measure_sinewave_simple(10, 0.1, 10))
    # results.append(measure_sinewave_simple(100, 0.1, 10))
    # results.append(measure_sinewave_simple(1000, 0.1, 10))
    results.append(measure_sinewave_simple(10000, 0.1, 10))
    results.append(measure_sinewave_simple(100000, 0.1, 10))
    results.append(measure_sinewave_simple(1000000, 0.1, 10))

    for r in results:
        print(r)
