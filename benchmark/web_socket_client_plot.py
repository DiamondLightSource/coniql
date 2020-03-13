import matplotlib.pyplot as plt
import json


def plot_web_socket_results(file: str, recording_time: int = 10):
    with open(file) as f:
        data = json.load(f)

    clean_data = {int(str(k)): v for k, v in data.items()}
    sorted_data = sorted(clean_data.items())
    # Found this trick here: https://stackoverflow.com/questions/37266341/plotting-a-python-dict-in-order-of-key-values/37266356
    subscriptions, rate = zip(*sorted_data)
    total_messages = []
    for index in range(len(subscriptions)):
        total_messages.append(subscriptions[index] * rate[index] * recording_time)

    fig, ax1 = plt.subplots()
    ax1.set_xlabel("Number of subscriptions")
    ax1.set_ylabel("Message Rate (Hz)", color="blue")
    ax1.plot(subscriptions, rate, color="blue")
    ax1.tick_params(axis="y", labelcolor="blue")

    ax2 = ax1.twinx()

    ax2.set_ylabel("Total Messages", color="red")
    ax2.plot(subscriptions, total_messages, color="red")
    ax2.tick_params(axis="y", labelcolor="red")

    fig.tight_layout()
    plt.show()


if __name__ == "__main__":
    plot_web_socket_results("/scratch/coniql/benchmark/web_socket_results_sine.json")
