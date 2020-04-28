class HelloClass:
    """A class who's only purpose in life is to say hello"""

    def __init__(self, name: str):
        """
        Args:
            name: The initial value of the name of the person who gets greeted
        """
        #: The name of the person who gets greeted
        self.name = name

    def format_greeting(self) -> str:
        """Return a greeting for `name`"""
        greeting = f"Hello {self.name}"
        return greeting
