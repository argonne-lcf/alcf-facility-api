# Get indents
def get_indent_strings(indent: int, base_indent: int):
    return " " * indent, " " * base_indent


# Dictionary to GraphQL
def dictionary_to_graphql_str(d: dict, base_indent: int = 0, indent: int = 4) -> str:
    """Convert an input dictionary into a GraphQL-compatible string."""

    # Generate indent spacings
    base_indent_str, indent_str = get_indent_strings(base_indent, indent)
    
    # Initialize the GraphQL-compatible string
    string = "{\n"

    # Convert each key-value pair in the dictionary
    for key, value in d.items():
        convertion = format_graphql_block(value, base_indent=base_indent, indent=indent)
        string += base_indent_str + indent_str + f"{key}: {convertion}\n"

    # Close the dictionary and return the string
    return f"{string}{base_indent_str}}}"


# List to GraphQL
def list_to_graphql_str(l: list, indent: int = 4, base_indent: int = 0) -> str:
    """Convert an input list into a GraphQL-compatible string."""
    
    # Generate indent spacings
    base_indent_str, indent_str = get_indent_strings(base_indent, indent)
    
    # Initialize the GraphQL-compatible string
    string = "[\n"
    
    # Convert each item in the list
    last_i = len(l) - 1
    for i, item in enumerate(l):
        convertion = format_graphql_block(item, base_indent=base_indent, indent=indent)
        string += base_indent_str + indent_str + convertion
        if i != last_i:
            string += ",\n"
                
    # Remove trailingClose the list and return the string
    return f"{string}\n{base_indent_str}]"


# Format GraphQL block
def format_graphql_block(block, base_indent: int = 0, indent: int = 4) -> str:
    """Generic fonction to format a block of a dictionary into a GraphQL-compatible string."""
    
    # String
    if isinstance(block, str):
        return f"\"{block}\""
    
    # Number
    elif isinstance (block, (int, float)):
        return block
    
    # List
    elif isinstance(block, list):
        return list_to_graphql_str(block, base_indent=base_indent+indent, indent=indent)
        
    # Dictionary
    elif isinstance(block, dict):
        return dictionary_to_graphql_str(block, base_indent=base_indent+indent, indent=indent)
        
    # Error for unsupported type
    else:
        raise Exception(f"Type {type(block)} not supported in format_graphql_block.")
    

# Build mutation createJob query
def build_mutation_createjob_query(input_data: dict = None) -> str:
    """Build a GraphQL-compatible string from input data for submitting a job."""
    return f"""
        mutation {{
            createJob (
                input: {dictionary_to_graphql_str(input_data, base_indent=16, indent=4)}
            ) {{
                node {{
                    jobId
                    status {{
                        state
                    }}
                }}
                error {{
                    errorCode
                    errorMessage
                }}
            }}
        }}
    """