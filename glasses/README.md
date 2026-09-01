# ALVIS Glasses

ALVIS Glasses is the HeyCyan companion build for the ALVIS project.

## Current approach

The first build uses the open-source CyanBridge Android implementation as the hardware bridge for HeyCyan glasses. That project already supports:

- HeyCyan BLE discovery/pairing/connection
- BLE control and device state
- BLE + Wi-Fi Direct media transfer
- camera/photo/video/audio operations exposed by the vendor SDK
- voice questions / image questions
- OpenAI-compatible remote inference
- local AI options

We intentionally do **not** flash firmware in this first stage. Firmware/OTA work will only be attempted after the exact hardware/firmware of the user's glasses is identified and backed up.

## ALVIS roadmap

1. Build and install ALVIS Glasses APK.
2. Pair the user's HeyCyan glasses.
3. Configure the OpenAI key inside the app/provider settings.
4. Route voice questions to ALVIS.
5. Route image questions to ALVIS Vision.
6. Add web search and spoken answers.
7. Add an ALVIS-specific always-listening/wake-word layer.
8. Only then investigate direct firmware customization.

The upstream project documents that HeyCyan uses BLE for control and Wi-Fi Direct for high-bandwidth media transfer. It also notes that hardware-specific commands must be validated on physical glasses.

Do not put an OpenAI API key in this repository or in GitHub Actions source. Configure it on the phone or through a protected backend.
