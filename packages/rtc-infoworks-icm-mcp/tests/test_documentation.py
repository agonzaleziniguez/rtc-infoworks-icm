import re
from importlib.resources import files
from pathlib import Path

from pydantic import TypeAdapter
from rtc_infoworks_icm_mcp.builder import build_definition
from rtc_infoworks_icm_mcp.models import BoundInput, parse_definition, parse_edits


def test_contract_json_examples_are_accepted() -> None:
    path = Path(__file__).parent.parent / "docs" / "contracts.md"
    examples = re.findall(r"```json\n(.*?)```", path.read_text(), re.DOTALL)
    assert len(examples) == 4
    for example in examples:
        if '"operations"' in example:
            build_definition(parse_definition(example))
        elif '"edits"' in example:
            parse_edits(example)
        else:
            TypeAdapter(tuple[BoundInput, ...]).validate_json(example)


def test_contract_python_example_runs() -> None:
    path = Path(__file__).parent.parent / "docs" / "contracts.md"
    examples = re.findall(r"```python\n(.*?)```", path.read_text(), re.DOTALL)
    assert len(examples) == 1
    namespace: dict[str, object] = {}
    exec(compile(examples[0], str(path), "exec"), namespace)
    text = namespace["rtc_text"]
    assert isinstance(text, str)
    assert text.endswith("TERMINATOR\n")


def test_element_guidance_is_a_packaged_resource() -> None:
    guidance = (
        files("rtc_infoworks_icm_mcp")
        .joinpath("resources", "elements.md")
        .read_text(encoding="utf-8")
    )
    assert guidance.startswith("# Supported RTC building blocks")
