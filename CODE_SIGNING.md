# Code signing policy

Windows releases of the CyberGems apps are not code-signed yet. This page explains why, what it means when you install, how every release is built, and how that will change. It is linked from the "Before you install" section of every release notes page.

## Why the releases are unsigned

The apps are free, open source hobby projects, and code signing certificates carry a recurring cost the project does not cover today. Once a certificate is in place, every Windows artifact will be signed before upload: the application executable, the installer, and the files shipped in the portable archive, because Smart App Control inspects every binary a program loads.

## What this means on Windows

- **SmartScreen**: the first time you run an installer or a portable executable, Windows may show the "Windows protected your PC" dialog. That is expected for unsigned programs and does not mean the file is unsafe. Click **More info** and then **Run anyway** to continue.
- **Smart App Control**: where it is on (typical on fresh Windows 11 installs), Windows refuses to run unsigned programs at all. There is no "Run anyway" button in that case: turn Smart App Control off, build the app from source, or wait for signed releases.
- **Verify a download**: every release notes page publishes the exact SHA256 of each artifact next to its VirusTotal report, and the source of every app is public, so you can also build the app yourself.

## How releases are built

- Every released file is built by GitHub Actions from a tagged commit. Nothing built on a person's machine is released.
- A release is created as a draft and reviewed before it is published, and the release notes publish the SHA256 of every artifact together with its VirusTotal link.
- The workflows and build scripts live in each repository and are reviewed like any other change.

## Network behavior

The apps ship with no telemetry, matching the principles in [CONTRIBUTING.md](CONTRIBUTING.md). Network access happens when a feature needs it, such as an update check against GitHub Releases or the downloads a feature exists for (for example fetching feeds in CyberFeeds). Each app's README describes its network features, and the public source lets you verify any call.
