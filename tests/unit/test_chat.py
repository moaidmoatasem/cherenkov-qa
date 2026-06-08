import unittest
import os
import tempfile
import json
from datetime import datetime

from cherenkov.chat.domain.models import Message, Session, Role
from cherenkov.chat.persona import Persona, PersonaRegistry
from cherenkov.chat.adapters.sqlite_memory import SQLiteConversationMemory
from cherenkov.chat.agent import QAChatAgent
from cherenkov.chat.tools import execute_tool, TOOL_REGISTRY, query_verdicts, query_idioms


class TestMessage(unittest.TestCase):
    def test_defaults(self):
        msg = Message(role="user", content="hello")
        self.assertEqual(msg.role, "user")
        self.assertEqual(msg.content, "hello")
        self.assertIsNotNone(msg.timestamp)
        self.assertIsNone(msg.tool_calls)

    def test_assistant_message(self):
        msg = Message(role="assistant", content="hi")
        self.assertEqual(msg.role, "assistant")

    def test_to_dict(self):
        msg = Message(role="user", content="test", session_id="s1")
        d = msg.to_dict()
        self.assertEqual(d["role"], "user")
        self.assertEqual(d["content"], "test")
        self.assertEqual(d["session_id"], "s1")
        self.assertIn("timestamp", d)


class TestSession(unittest.TestCase):
    def test_defaults(self):
        ses = Session(session_id="s1")
        self.assertEqual(ses.session_id, "s1")
        self.assertEqual(ses.persona_id, "qa_assistant")
        self.assertEqual(len(ses.messages), 0)
        self.assertEqual(ses.metadata, {})

    def test_to_dict(self):
        ses = Session(session_id="s1", persona_id="custom")
        d = ses.to_dict()
        self.assertEqual(d["session_id"], "s1")
        self.assertEqual(d["persona_id"], "custom")
        self.assertEqual(d["message_count"], 0)


class TestPersona(unittest.TestCase):
    def test_default_persona(self):
        p = Persona(persona_id="qa", name="QA", description="helper",
                     system_prompt="You are QA")
        self.assertEqual(p.persona_id, "qa")
        self.assertEqual(p.temperature, 0.1)

    def test_custom_temperature(self):
        p = Persona(persona_id="t", name="T", description="d",
                     system_prompt="prompt", temperature=0.5)
        self.assertEqual(p.temperature, 0.5)


class TestPersonaRegistry(unittest.TestCase):
    def setUp(self):
        self.registry = PersonaRegistry()

    def test_default_persona_exists(self):
        p = self.registry.get("qa_assistant")
        self.assertIsNotNone(p)
        self.assertEqual(p.persona_id, "qa_assistant")

    def test_get_unknown_returns_none(self):
        p = self.registry.get("does_not_exist")
        self.assertIsNone(p)

    def test_register_and_get(self):
        custom = Persona(persona_id="custom", name="Custom", description="D",
                          system_prompt="you are custom")
        self.registry.register(custom)
        p = self.registry.get("custom")
        self.assertIsNotNone(p)
        self.assertEqual(p.name, "Custom")

    def test_list_personas(self):
        personas = self.registry.list_personas()
        self.assertEqual(len(personas), 1)
        self.assertEqual(personas[0].persona_id, "qa_assistant")

    def test_compose_prompt_basic(self):
        prompt = self.registry.compose_prompt("qa_assistant")
        self.assertIn("QA assistant", prompt)

    def test_compose_prompt_with_context(self):
        context = {"project_context": "Test project", "idioms": ["idiom1", "idiom2"]}
        prompt = self.registry.compose_prompt("qa_assistant", context)
        self.assertIn("Test project", prompt)
        self.assertIn("idiom1", prompt)

    def test_compose_prompt_unknown_persona_falls_back(self):
        prompt = self.registry.compose_prompt("nonexistent")
        self.assertIn("QA assistant", prompt)


class TestSQLiteConversationMemory(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.tmp.name
        self.tmp.close()
        self.memory = SQLiteConversationMemory(self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_create_and_get_session(self):
        ses = self.memory.create_session("session-1")
        self.assertEqual(ses.session_id, "session-1")
        loaded = self.memory.get_session("session-1")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.session_id, "session-1")

    def test_get_nonexistent_session(self):
        self.assertIsNone(self.memory.get_session("nope"))

    def test_add_and_get_messages(self):
        self.memory.create_session("s1")
        msg1 = Message(role="user", content="hello")
        msg2 = Message(role="assistant", content="hi")
        self.memory.add_message("s1", msg1)
        self.memory.add_message("s1", msg2)
        messages = self.memory.get_messages("s1")
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0].content, "hello")
        self.assertEqual(messages[1].content, "hi")

    def test_get_messages_empty_session(self):
        self.memory.create_session("s1")
        messages = self.memory.get_messages("s1")
        self.assertEqual(len(messages), 0)

    def test_get_messages_limit(self):
        self.memory.create_session("s1")
        for i in range(5):
            self.memory.add_message("s1", Message(role="user", content=str(i)))
        messages = self.memory.get_messages("s1", limit=3)
        self.assertEqual(len(messages), 3)

    def test_close_session(self):
        self.memory.create_session("s1")
        self.memory.close_session("s1")
        loaded = self.memory.get_session("s1")
        self.assertIsNone(loaded)

    def test_list_sessions(self):
        self.memory.create_session("s1")
        self.memory.create_session("s2")
        sessions = self.memory.list_sessions()
        self.assertEqual(len(sessions), 2)

    def test_list_sessions_excludes_closed(self):
        self.memory.create_session("s1")
        self.memory.create_session("s2")
        self.memory.close_session("s1")
        sessions = self.memory.list_sessions()
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0].session_id, "s2")

    def test_message_with_tool_calls(self):
        self.memory.create_session("s1")
        msg = Message(role="assistant", content="tool result",
                       tool_calls=[{"name": "query_verdicts"}])
        self.memory.add_message("s1", msg)
        messages = self.memory.get_messages("s1")
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].tool_calls, [{"name": "query_verdicts"}])


class TestQAChatAgent(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.tmp.name
        self.tmp.close()
        self.memory = SQLiteConversationMemory(self.db_path)
        self.registry = PersonaRegistry()
        self.agent = QAChatAgent(memory=self.memory, persona_registry=self.registry)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_create_session(self):
        ses = self.agent.create_session()
        self.assertIsNotNone(ses.session_id)
        self.assertEqual(ses.persona_id, "qa_assistant")

    def test_create_session_custom_persona(self):
        custom = Persona(persona_id="custom", name="Custom", description="D",
                          system_prompt="custom prompt")
        self.registry.register(custom)
        ses = self.agent.create_session(persona_id="custom")
        self.assertEqual(ses.persona_id, "custom")

    def test_get_session(self):
        ses = self.agent.create_session()
        loaded = self.agent.get_session(ses.session_id)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.session_id, ses.session_id)

    def test_add_user_message(self):
        ses = self.agent.create_session()
        msg = self.agent.add_user_message(ses.session_id, "hello")
        self.assertEqual(msg.role, "user")
        self.assertEqual(msg.content, "hello")
        history = self.memory.get_messages(ses.session_id)
        self.assertEqual(len(history), 1)

    def test_chat_returns_assistant_message(self):
        ses = self.agent.create_session()
        response = self.agent.chat(ses.session_id, "What verdicts exist?")
        self.assertEqual(response.role, "assistant")
        self.assertTrue(len(response.content) > 0)

    def test_chat_persists_assistant_response(self):
        ses = self.agent.create_session()
        self.agent.chat(ses.session_id, "Tell me about divergences")
        history = self.memory.get_messages(ses.session_id)
        roles = [m.role for m in history]
        self.assertIn("user", roles)
        self.assertIn("assistant", roles)

    def test_chat_with_unknown_session_falls_back(self):
        response = self.agent.chat("unknown-session", "hello")
        self.assertEqual(response.role, "assistant")

    async def test_chat_stream_yields_tokens(self):
        ses = self.agent.create_session()
        tokens = []
        async for token in self.agent.chat_stream(ses.session_id, "hello"):
            tokens.append(token)
        self.assertTrue(len(tokens) > 0)
        history = self.memory.get_messages(ses.session_id)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0].role, "user")
        self.assertEqual(history[1].role, "assistant")


class TestTools(unittest.TestCase):
    def test_tool_registry_has_expected_tools(self):
        self.assertIn("query_verdicts", TOOL_REGISTRY)
        self.assertIn("query_idioms", TOOL_REGISTRY)
        self.assertIn("explain_divergence", TOOL_REGISTRY)
        self.assertIn("run_test", TOOL_REGISTRY)

    def test_query_verdicts_returns_dict(self):
        result = query_verdicts()
        self.assertIsInstance(result, dict)
        self.assertIn("verdicts", result)

    def test_query_idioms_returns_dict(self):
        result = query_idioms()
        self.assertIsInstance(result, dict)
        self.assertIn("idioms", result)

    def test_execute_unknown_tool(self):
        result = execute_tool("nonexistent")
        self.assertIn("error", result)


if __name__ == "__main__":
    unittest.main()
