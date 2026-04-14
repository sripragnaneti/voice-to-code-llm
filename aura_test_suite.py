import unittest
import os
import shutil
import json
from unittest.mock import MagicMock, patch
import tools
import config_utils
from agent import LocalAIAgent

class TestAuraTools(unittest.TestCase):
    def setUp(self):
        self.test_dir = "test_output"
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        os.makedirs(self.test_dir)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_secure_path(self):
        # Valid path
        path = tools.secure_path(self.test_dir, "test.txt")
        self.assertTrue(path.startswith(os.path.abspath(self.test_dir)))
        
        # Security violation (traversal)
        with self.assertRaises(Exception):
            tools.secure_path(self.test_dir, "../outside.txt")

    def test_create_file_and_list(self):
        tools.create_file(self.test_dir, "hello.py", "print('hello')")
        files = tools.list_files(self.test_dir)
        self.assertIn("hello.py", files)

    def test_verify_python_syntax(self):
        fp = os.path.join(self.test_dir, "valid.py")
        tools.create_file(self.test_dir, "valid.py", "def main():\n    pass")
        success, msg = tools.verify_code(fp)
        self.assertTrue(success)
        
        fp_err = os.path.join(self.test_dir, "invalid.py")
        tools.create_file(self.test_dir, "invalid.py", "def main(:\n    pass")
        success, msg = tools.verify_code(fp_err)
        self.assertFalse(success)

class TestAuraConfig(unittest.TestCase):
    @patch('os.getenv')
    def test_get_available_apis(self, mock_getenv):
        # Test when GROQ_API_KEY is present
        mock_getenv.return_value = "some_key"
        apis = config_utils.get_available_apis()
        self.assertIn("groq", apis)
        
        # Test when absent
        mock_getenv.return_value = None
        apis = config_utils.get_available_apis()
        self.assertNotIn("groq", apis)

class TestAuraAgent(unittest.TestCase):
    @patch('agent.ollama.list')
    def test_agent_init_local(self, mock_ollama_list):
        # Mocking ollama.list inside agent.py
        mock_res = MagicMock()
        mock_res.models = [MagicMock(model="llama3")]
        mock_ollama_list.return_value = mock_res
        
        agent = LocalAIAgent(mode="local")
        self.assertEqual(agent.provider, "ollama")
        self.assertEqual(agent.model_name, "llama3")

    @patch('agent.Groq')
    @patch('os.getenv')
    def test_agent_init_global_groq(self, mock_getenv, mock_groq):
        mock_getenv.side_effect = lambda k: "gsk_test" if k == "GROQ_API_KEY" else None
        agent = LocalAIAgent(mode="global")
        self.assertEqual(agent.provider, "groq")
        self.assertTrue(agent.model_name.startswith("llama-3.3"))

    @patch.object(LocalAIAgent, '_chat')
    def test_agent_intent_recognition(self, mock_chat):
        # Mock orchestrator JSON output
        agent = LocalAIAgent(mode="local", model_name="llama3")
        # We also need to mock the specialized generation chat call
        mock_chat.side_effect = [
            '{"intent": "write_code", "language": "python", "target_file": "script.py"}', # Orchestrator
            "print('hello world')" # Python Generator
        ]
        
        res = agent.get_intent_and_refine("write a script that prints hello world")
        self.assertEqual(res["intent"], "write_code")
        self.assertEqual(res["filename"], "script.py")
        self.assertEqual(res["content"], "print('hello world')")

    @patch('agent.Groq')
    @patch('os.getenv')
    def test_groq_api_call_logic(self, mock_getenv, mock_groq_class):
        mock_getenv.side_effect = lambda k: "gsk_test" if k == "GROQ_API_KEY" else None
        
        # Mock Groq client and response
        mock_client = MagicMock()
        mock_groq_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Groq Response"
        mock_client.chat.completions.create.return_value = mock_response
        
        agent = LocalAIAgent(mode="global")
        result = agent._chat([{"role": "user", "content": "hi"}])
        
        self.assertEqual(result, "Groq Response")
        mock_client.chat.completions.create.assert_called_once()

class TestAuraToolsExtended(unittest.TestCase):
    @patch('shutil.which')
    @patch('subprocess.run')
    def test_verify_java_success(self, mock_run, mock_which):
        mock_which.return_value = "/usr/bin/javac"
        mock_run.return_value = MagicMock(returncode=0)
        
        with patch('builtins.open', unittest.mock.mock_open(read_data="class Test {}")):
            with patch('os.path.exists', return_value=True):
                success, msg = tools.verify_code("Test.java")
                self.assertTrue(success)
                self.assertIn("Valid", msg)

    @patch('shutil.which')
    @patch('subprocess.run')
    def test_verify_c_failure(self, mock_run, mock_which):
        mock_which.return_value = "/usr/bin/gcc"
        mock_run.return_value = MagicMock(returncode=1, stderr="syntax error")
        
        with patch('os.path.exists', return_value=True):
            success, msg = tools.verify_code("test.c")
            self.assertFalse(success)
            self.assertIn("Syntax Error", msg)

if __name__ == "__main__":
    unittest.main()
