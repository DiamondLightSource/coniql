from measure import measure_request_times, print_request_times

sine_query_full = """
query {
  getChannel(id: "sim://sine") {
    id
    meta {
      __typename
      description
      tags
      label
      ... on ObjectMeta {
        array
        type
      }
      ... on NumberMeta {
        array
        numberType
        display {
          controlRange {
            min
            max
          }
          displayRange {
            min
            max
          }
          alarmRange {
            min
            max
          }
          warningRange {
            min
            max
          }
          units
          precision
          form
        }
      }
      ... on EnumMeta {
        array
        choices
      }
    }
    value
    time {
      seconds
      nanoseconds
      userTag
    }
    status {
      quality
      message
      mutable
    }
  }
}
"""

sine_query_value_only = """
query {
  getChannel(id: "sim://sine") {
    value
  }
}
"""


if __name__ == "__main__":
    print_request_times(measure_request_times(query=sine_query_full), "Sine Query Full")
    print_request_times(
        measure_request_times(query=sine_query_value_only), "Sine Query Value Only"
    )

