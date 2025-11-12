def image_parsing_prompt() -> str:
    return (
        "Extract all possible text and information from the image including any charts, tables, graphs, trends, diagrams and visual descriptions. Don't make up any information. Only output the extracted information without any imagination."
    )
