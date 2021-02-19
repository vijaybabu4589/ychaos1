#  Copyright 2021, Verizon Media
#  Licensed under the terms of the ${MY_OSI} license. See the LICENSE file in the project root for terms

import json
import tempfile
from pathlib import Path
from unittest import TestCase

import jsondiff
from pkg_resources import resource_filename

from vzmi.ychaos.testplan import SystemState
from vzmi.ychaos.testplan.attack import (
    AttackConfig,
    TargetType,
    MachineTargetDefinition,
)
from vzmi.ychaos.testplan.schema import TestPlan, TestPlanSchema
from vzmi.ychaos.testplan.verification import (
    VerificationConfig,
    PythonModuleVerification,
)


class TestSchemaDataClass(TestCase):
    def setUp(self) -> None:
        self.testplans_directory = (
            Path(__file__).joinpath("../../resources/testplans").resolve()
        )
        self.assertTrue(
            str(self.testplans_directory).endswith("tests/resources/testplans")
        )

        self.mock_testplan = TestPlan(
            verification=[
                VerificationConfig(
                    states=[SystemState.STEADY, SystemState.RECOVERED],
                    type="python_module",
                    config=dict(path="/directory/subdirectory/script.py"),
                ),
                VerificationConfig(
                    states=SystemState.CHAOS,
                    type="python_module",
                    config=dict(path="/directory/subdirectory/script.py"),
                ),
            ],
            attack=AttackConfig(
                target_type=TargetType.MACHINE,
                target_config=MachineTargetDefinition(
                    blast_radius=34,
                    hostnames=[
                        "mockhost1.yahoo.com",
                        "mockhost2.yahoo.com",
                        "mockhost3.yahoo.com",
                    ],
                    hostpatterns=["web[01-05].fe.yahoo.com", "mockhost4.yahoo.com"],
                ).dict(),
                agents=[dict(type="no_op", config=dict(name="no_op"))],
            ),
        )

    def test_testplan_construction(self):
        self.assertIsNotNone(self.mock_testplan.id)
        self.assertEqual(len(self.mock_testplan.verification), 2)
        self.assertEqual(
            len(self.mock_testplan.filter_verification_by_state(SystemState.CHAOS)), 1
        )
        self.assertEqual(
            len(self.mock_testplan.filter_verification_by_state(SystemState.RECOVERED)),
            1,
        )

        self.assertIsInstance(
            self.mock_testplan.verification[0].get_verification_config(),
            PythonModuleVerification,
        )

        self.assertIsInstance(self.mock_testplan.attack, AttackConfig)
        self.assertEqual(len(self.mock_testplan.attack.agents), 1)
        self.assertListEqual(
            self.mock_testplan.attack.get_target_config().hostnames,
            ["mockhost1.yahoo.com", "mockhost2.yahoo.com", "mockhost3.yahoo.com"],
        )

        self.assertListEqual(
            self.mock_testplan.attack.get_target_config().hostpatterns,
            ["web[01-05].fe.yahoo.com", "mockhost4.yahoo.com"],
        )
        self.assertListEqual(
            self.mock_testplan.attack.get_target_config().expand_hostpatterns(),
            [
                "web01.fe.yahoo.com",
                "web02.fe.yahoo.com",
                "web03.fe.yahoo.com",
                "web04.fe.yahoo.com",
                "web05.fe.yahoo.com",
                "mockhost4.yahoo.com",
            ],
        )

    def test_testplan_schema_is_updated(self):
        # Validate the schema.json is up to date
        current_schema = TestPlanSchema.schema()

        PKG_RESOURCES = "vzmi.ychaos.testplan.resources"
        AUTOGEN_SCHEMA_FILE = str(resource_filename(PKG_RESOURCES, "schema.json"))

        schema_file = Path(AUTOGEN_SCHEMA_FILE)
        autogenerated_schema = json.loads(schema_file.read_text())

        difference = jsondiff.diff(current_schema, autogenerated_schema)

        if difference:
            print(difference)

        self.assertFalse(difference)

    def test_testplan_load_from_file(self):
        testplan = TestPlan.load_file(
            self.testplans_directory.joinpath("valid/testplan1.json")
        )
        self.assertEqual(testplan.description, "A valid mock testplan file")

    def test_testplan_export_to_json_file(self):
        temporary_file = tempfile.NamedTemporaryFile("w+")

        self.mock_testplan.export_to_file(temporary_file.name)
        testplan_from_file = TestPlan.load_file(temporary_file.name)
        self.assertEqual(self.mock_testplan, testplan_from_file)

        temporary_file.close()

    def test_testplan_export_to_yaml_file(self):
        temporary_file = tempfile.NamedTemporaryFile("w+")

        self.mock_testplan.export_to_file(temporary_file.name, yaml_format=True)
        testplan_from_file = TestPlan.load_file(temporary_file.name)
        self.assertEqual(self.mock_testplan, testplan_from_file)

        temporary_file.close()
