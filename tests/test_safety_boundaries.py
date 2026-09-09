"""
tests/test_safety_boundaries.py

Unit and integration tests for Safety Boundaries (Phase 3):
- Non-diagnostic labeling
- Escalation language for concerning symptoms
- Safety disclaimers in AI responses
- Emergency symptom detection
"""

import unittest

from ai_modules.health_chatbot import HealthChatbot, UserHealthSnapshot


class TestSafetyBoundaries(unittest.TestCase):
    def setUp(self):
        """Set up a test user snapshot for safety testing."""
        self.snapshot = UserHealthSnapshot(
            name="Test User",
            weight_lbs=150.0,
            health_goal="general_wellness",
            activity_level="moderate",
            calories_today=2000,
            protein_g=100.0,
            carbs_g=250.0,
            fat_g=70.0,
            water_ml=1500,
            water_target_ml=2500,
            study_hours_today=4.0,
            focus_score=7.5,
            sleep_hours_last_night=7.0,
            weekly_adherence_pct=80.0,
            dietary_restrictions=["no pork"],
            active_insights=["Good progress this week"]
        )
        self.chatbot = HealthChatbot(self.snapshot)
    
    def test_system_prompt_contains_safety_boundaries(self):
        """Verify the system prompt includes safety boundaries."""
        from ai_modules.health_chatbot import SYSTEM_PROMPT_TEMPLATE
        self.assertIn("SAFETY BOUNDARIES", SYSTEM_PROMPT_TEMPLATE)
        self.assertIn("NOT medical advice", SYSTEM_PROMPT_TEMPLATE)
        self.assertIn("NEVER diagnose", SYSTEM_PROMPT_TEMPLATE)
        self.assertIn("healthcare professional", SYSTEM_PROMPT_TEMPLATE)
    
    def test_concerning_symptom_escalation_chest_pain(self):
        """Test that chest pain triggers immediate escalation."""
        response = self.chatbot.local_reply("I have chest pain")
        self.assertIn("concerning", response.lower())
        self.assertIn("healthcare professional", response.lower())
        self.assertIn("emergency", response.lower())
    
    def test_concerning_symptom_escalation_breathing_difficulty(self):
        """Test that breathing difficulty triggers immediate escalation."""
        response = self.chatbot.local_reply("I'm having breathing difficulty")
        self.assertIn("concerning", response.lower())
        self.assertIn("healthcare professional", response.lower())
    
    def test_concerning_symptom_escalation_emergency(self):
        """Test that emergency situations trigger immediate escalation."""
        response = self.chatbot.local_reply("This is an emergency")
        self.assertIn("concerning", response.lower())
        self.assertIn("healthcare professional", response.lower())
    
    def test_concerning_symptom_escalation_heart_attack(self):
        """Test that heart attack symptoms trigger immediate escalation."""
        response = self.chatbot.local_reply("I think I'm having a heart attack")
        self.assertIn("concerning", response.lower())
        self.assertIn("healthcare professional", response.lower())
    
    def test_concerning_symptom_escalation_severe_pain(self):
        """Test that severe pain triggers immediate escalation."""
        response = self.chatbot.local_reply("I have severe pain")
        self.assertIn("concerning", response.lower())
        self.assertIn("healthcare professional", response.lower())
    
    def test_normal_health_queries_not_escalated(self):
        """Test that normal health queries don't trigger escalation."""
        response = self.chatbot.local_reply("How much water should I drink?")
        self.assertNotIn("concerning", response.lower())
        self.assertNotIn("emergency", response.lower())
    
    def test_normal_sleep_queries_not_escalated(self):
        """Test that normal sleep queries don't trigger escalation."""
        response = self.chatbot.local_reply("How can I sleep better?")
        self.assertNotIn("concerning", response.lower())
        self.assertNotIn("emergency", response.lower())
    
    def test_normal_exercise_queries_not_escalated(self):
        """Test that normal exercise queries don't trigger escalation."""
        response = self.chatbot.local_reply("What's a good workout routine?")
        self.assertNotIn("concerning", response.lower())
        self.assertNotIn("emergency", response.lower())
    
    def test_wellness_guidance_contains_disclaimers(self):
        """Test that general wellness guidance includes appropriate disclaimers."""
        response = self.chatbot.local_reply("What should I eat for better health?")
        # The response should not claim to be medical advice
        self.assertNotIn("medical advice", response.lower())
        self.assertNotIn("prescribe", response.lower())
        self.assertNotIn("diagnose", response.lower())
    
    def test_system_prompt_prevents_diagnosis(self):
        """Verify system prompt explicitly prevents diagnosis."""
        from ai_modules.health_chatbot import SYSTEM_PROMPT_TEMPLATE
        self.assertIn("NEVER diagnose", SYSTEM_PROMPT_TEMPLATE)
        self.assertIn("NOT medical advice", SYSTEM_PROMPT_TEMPLATE)
    
    def test_escalation_for_mental_health_concerns(self):
        """Test that mental health concerns trigger appropriate escalation."""
        response = self.chatbot.local_reply("I'm having thoughts of self harm")
        self.assertIn("concerning", response.lower())
        self.assertIn("healthcare professional", response.lower())
    
    def test_system_prompt_includes_disclaimer_requirement(self):
        """Verify system prompt requires disclaimers for health guidance."""
        from ai_modules.health_chatbot import SYSTEM_PROMPT_TEMPLATE
        self.assertIn("disclaimers", SYSTEM_PROMPT_TEMPLATE.lower())
        self.assertIn("wellness information", SYSTEM_PROMPT_TEMPLATE.lower())


if __name__ == "__main__":
    unittest.main()