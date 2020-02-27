class Completion:
    async def reset(self):
        return NotImplemented


class ArmedScheme:
    async def run(self) -> Completion:
        return NotImplemented


class Scheme:
    async def prepare(self) -> ArmedScheme:
        return NotImplemented
