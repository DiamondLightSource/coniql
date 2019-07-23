from annotypes import Anno, add_call_types

with Anno("Who to greet"):
    APerson = str
with Anno("The greeting to return"):
    AGreeting = str


@add_call_types
def say_hello(person: APerson="me") -> AGreeting:
    """Say hello to person"""
    return f'Hello %s' % person
