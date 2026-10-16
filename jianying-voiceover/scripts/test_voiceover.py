import json
from pathlib import Path
import tempfile
import unittest
import wave

import voiceover


class VoiceoverTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.clips = self.root/"clips"
        self.clips.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def wav(self, number, seconds, rate=8000):
        path = self.clips/f"segment-{number:03d}.wav"
        with wave.open(str(path), "wb") as out:
            out.setnchannels(1)
            out.setsampwidth(2)
            out.setframerate(rate)
            out.writeframes(b"\x00\x00"*round(seconds*rate))

    def script(self, segments):
        path = self.root/"script.json"
        path.write_text(json.dumps({"language":"pt-BR", "segments":segments}), encoding="utf-8")
        return voiceover.load_script(path)

    def test_measured_timing_padding_and_srt(self):
        self.wav(1, 0.4)
        self.wav(2, 0.6)
        data = self.script([{"text":"Primeira frase.", "target_duration":0.8, "pause_after":0.1},
                            {"text":"Segunda frase.", "pause_after":0}])
        result = voiceover.assemble(data, self.clips, self.root/"out")
        self.assertAlmostEqual(result["duration"], 1.4)
        self.assertEqual(result["captions"][1]["start"], 0.8)
        self.assertFalse(result["requires_timing_review"])
        with wave.open(result["narration"], "rb") as audio:
            self.assertEqual(audio.getnframes(), 11200)
        self.assertIn("00:00:00,800 --> 00:00:01,400", Path(result["subtitles"]).read_text(encoding="utf-8"))

    def test_overflow_keeps_complete_audio(self):
        self.wav(1, 0.4)
        data = self.script([{"text":"Frase inteira.", "target_duration":0.2, "pause_after":0}])
        result = voiceover.assemble(data, self.clips, self.root/"out")
        self.assertTrue(result["requires_timing_review"])
        self.assertAlmostEqual(result["segments"][0]["overflow_seconds"], 0.2)
        self.assertEqual(result["duration"], 0.4)

    def test_incompatible_wavs_are_rejected_before_combining(self):
        self.wav(1, 0.4)
        self.wav(2, 0.4, 16000)
        data = self.script([{"text":"One"}, {"text":"Two"}])
        with self.assertRaisesRegex(ValueError, "matching PCM"):
            voiceover.assemble(data, self.clips, self.root/"out")
        self.assertFalse((self.root/"out/narration.wav").exists())

    def test_attachment_preserves_source_paths_and_rejects_long_audio(self):
        self.wav(1, 0.4)
        data = self.script([{"text":"Frase inteira.", "pause_after":0}])
        voiceover.assemble(data, self.clips, self.root/"out")
        plan = self.root/"plan.json"
        plan.write_text(json.dumps({"projects":[{"name":"test", "music":"music.wav", "shots":[{"source":"a.mp4", "target_duration":1}]}]}), encoding="utf-8")
        dest = self.root/"relocated/plan.json"
        voiceover.attach(plan, "test", self.root/"out/voiceover.json", dest)
        attached = json.loads(dest.read_text(encoding="utf-8"))["projects"][0]
        self.assertEqual(attached["shots"][0]["source"], str((self.root/"a.mp4").resolve()))
        self.assertEqual(attached["music"], str((self.root/"music.wav").resolve()))
        plan.write_text(json.dumps({"projects":[{"name":"test", "shots":[{"source":"a.mp4", "target_duration":0.1}]}]}), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "exceeds planned"):
            voiceover.attach(plan, "test", self.root/"out/voiceover.json", self.root/"too-long.json")


if __name__ == "__main__":
    unittest.main()
