from dataclasses import dataclass

from scanpointgenerator import CompoundGenerator


@dataclass
class TrajectoryModel:
    generator: CompoundGenerator
    start_index: int
    end_index: int

    @classmethod
    def do_steps(cls, generator: CompoundGenerator, start_index: int, steps_to_do: int):
        return TrajectoryModel(generator, start_index, start_index + steps_to_do)

    @classmethod
    def all_steps(cls, generator: CompoundGenerator):
        generator.prepare()
        steps_to_do = len(list(generator.iterator()))
        return cls.do_steps(generator, 0, steps_to_do)

    @classmethod
    def from_dict(cls, dct):
        end_index = dct['end_index']
        generator = dct['generator']
        if end_index < 0:
            generator.prepare()
            end_index = len(list(generator.iterator()))
        return TrajectoryModel(
            generator,
            dct['start_index'],
            end_index
        )

    def with_revised_generator(self, revised_generator: CompoundGenerator):
        return TrajectoryModel(revised_generator,
                               self.start_index, self.end_index)
