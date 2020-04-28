from coniql._types import HelloClass


def say_hello_lots(hello: HelloClass = None, times=5):
    """Print lots of greetings using the given `HelloClass`

    Args:
        hello: A `HelloClass` that `format_greeting` will be called on.
            If not given, use a HelloClass with name="me"
        times: The number of times to call it
    """
    if hello is None:
        hello = HelloClass("me")
    for _ in range(times):
        print(hello.format_greeting())
