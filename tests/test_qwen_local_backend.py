import json
import wave

import pytest

from betman_voice.inference.backends import _qwen_profile_id, _qwen_profile_reference
from betman_voice.services.elevenlabs_import import BETMAN_ELEVENLABS_VOICES

EXPECTED_MAPPINGS = {
    "2Ei5B6ir7ZzmLurX6KU4": (
        "betman-female-presenter",
        "qwen:9f0d5d97-93a7-46a8-a0af-9260e60ab3e2",
    ),
    "9K2UBMDog21eSfMdLhEX": (
        "betman-comms-girl",
        "qwen:67de3c0d-acbd-4236-a120-910c4e569c75",
    ),
    "hp7ETPcMxGdsmsPtJd8I": (
        "paul-social-outgoing-kind",
        "qwen:93bd7993-4d63-4937-b3c1-2e76602b062f",
    ),
    "pDZ0CqONaFi2LrK1f413": (
        "torey-slatter",
        "qwen:fd581ac5-5f66-49a5-a596-e5986d65bcbc",
    ),
}


def test_all_elevenlabs_presenters_have_distinct_qwen_profiles_and_aliases():
    actual = {
        spec["voice_id"]: (spec["local_alias"], spec["model_ref"])
        for spec in BETMAN_ELEVENLABS_VOICES
    }
    assert actual == EXPECTED_MAPPINGS
    assert len({model_ref for _, model_ref in actual.values()}) == len(actual)


def test_qwen_profile_reference_uses_exported_sample_and_transcript(tmp_path):
    profile_id = "9f0d5d97-93a7-46a8-a0af-9260e60ab3e2"
    profile_dir = tmp_path / profile_id
    samples_dir = profile_dir / "samples"
    samples_dir.mkdir(parents=True)
    reference = samples_dir / "reference.wav"
    with wave.open(str(reference), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(24_000)
        audio.writeframes(b"\x00\x00" * 2_400)
    (profile_dir / "samples.json").write_text(
        json.dumps({"reference.wav": "BETMAN reference transcript."})
    )

    path, transcript = _qwen_profile_reference(tmp_path, profile_id)

    assert path == reference
    assert transcript == "BETMAN reference transcript."
    assert _qwen_profile_id(f"qwen:{profile_id}") == profile_id


@pytest.mark.parametrize("model_ref", ["", "piper:amy", "qwen:../../escape", "qwen:bad id"])
def test_qwen_profile_id_rejects_invalid_refs(model_ref):
    with pytest.raises(RuntimeError):
        _qwen_profile_id(model_ref)
