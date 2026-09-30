#!/usr/bin/env python3
"""skills/knowledge-base: the shipped schemas are valid Basic Memory schemas, and every template passes its own.

Basic Memory checks notes against schemas itself (`basic-memory tool schema-validate <type>`). This checks
the same rules without it: a required field is an observation category (`- [purpose] ...`) or, for a
capitalized type, a relation (`- depends_on [[X]]`); a frontmatter enum takes only its listed values.

Run: python3 -m unittest discover -s skills/knowledge-base/tests
"""

import os
import re
import unittest

import yaml

SKILL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SCHEMAS = os.path.join(SKILL, "schemas")
TEMPLATES = os.path.join(SKILL, "templates")
TYPES = ["agreement", "debt", "decision", "rule", "system", "team"]
SCALARS = {"string", "integer", "number", "boolean", "any"}


def split(path):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    assert m, f"{path}: no frontmatter"
    return yaml.safe_load(m.group(1)), m.group(2)


def fields(schema):
    """[(name, required, is_relation, enum_values)] from a Picoschema dict, as Basic Memory reads it."""
    out = []
    for key, value in schema.items():
        m = re.match(r"^([a-z_]+)(\?)?(?:\((array|enum|object)[^)]*\))?$", key)
        assert m, f"unreadable field key {key!r}"
        name, optional, modifier = m.groups()
        if modifier == "enum":
            out.append((name, not optional, False, [str(v) for v in value]))
            continue
        type_ = str(value).split(",")[0].strip()
        out.append((name, not optional, type_ not in SCALARS and type_[:1].isupper(), None))
    return out


def body_parts(body):
    categories = set(re.findall(r"^- \[([a-z_]+)\] ", body, re.M))
    relations = set(re.findall(r"^- ([a-z_]+) \[\[[^\]]+\]\]", body, re.M))
    return categories, relations


class Schemas(unittest.TestCase):
    def test_every_type_has_a_schema_named_for_it(self):
        self.assertEqual(sorted(f[:-3] for f in os.listdir(SCHEMAS) if f.endswith(".md")), TYPES)
        for t in TYPES:
            front, _ = split(os.path.join(SCHEMAS, f"{t}.md"))
            self.assertEqual((front["type"], front["entity"], front["title"]), ("schema", t, t))
            self.assertEqual(front["settings"]["validation"], "warn", t)   # a gap is a warning, never a lost note
            self.assertTrue(fields(front["schema"]), t)

    def test_relations_point_at_types_that_exist(self):
        for t in TYPES:
            front, _ = split(os.path.join(SCHEMAS, f"{t}.md"))
            for key, value in front["schema"].items():
                type_ = str(value).split(",")[0].strip()
                if type_[:1].isupper():
                    self.assertIn(type_.lower(), TYPES, f"{t}.{key} -> {type_}")


class Templates(unittest.TestCase):
    def test_every_template_passes_its_schema(self):
        self.assertEqual(sorted(f[:-3] for f in os.listdir(TEMPLATES) if f.endswith(".md")), TYPES)
        for t in TYPES:
            schema, _ = split(os.path.join(SCHEMAS, f"{t}.md"))
            front, body = split(os.path.join(TEMPLATES, f"{t}.md"))
            self.assertEqual(front["type"], t)
            categories, relations = body_parts(body)
            known = set()
            for name, required, is_relation, _ in fields(schema["schema"]):
                known.add(name)
                if required:
                    self.assertIn(name, relations if is_relation else categories, f"{t}: missing {name}")
            self.assertEqual((categories | relations) - known, set(), f"{t}: fields the schema does not know")
            for name, required, _, enum in fields(schema["settings"].get("frontmatter", {})):
                if required:
                    self.assertIn(name, front, f"{t}: missing frontmatter {name}")
                if enum:
                    self.assertIn(str(front[name]), enum, f"{t}: {name}")


if __name__ == "__main__":
    unittest.main()
