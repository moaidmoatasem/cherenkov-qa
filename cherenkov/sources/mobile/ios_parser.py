from __future__ import annotations
from pathlib import Path
from cherenkov.sources.mobile.contracts import MobileApp


class IPAParser:
    """Parse iOS IPA metadata (stub — requires codesign/otool on macOS)."""

    def parse(self, ipa_path: str) -> MobileApp:
        ipa = Path(ipa_path)
        if not ipa.exists():
            raise FileNotFoundError(f"IPA not found: {ipa_path}")
        # Real parsing requires macOS codesign toolchain; return stub with path info
        return MobileApp(
            app_id=ipa.stem,
            name=ipa.stem,
            platform="ios",
            version="0.0.0",
            package_path=str(ipa.resolve()),
        )


class PlistParser:
    """Parse iOS Info.plist for app metadata."""

    def parse(self, plist_path: str) -> MobileApp:
        plist = Path(plist_path)
        if not plist.exists():
            raise FileNotFoundError(f"plist not found: {plist_path}")
        try:
            import plistlib

            with open(plist, "rb") as f:
                data = plistlib.load(f)
            return MobileApp(
                app_id=data.get("CFBundleIdentifier", plist.stem),
                name=data.get(
                    "CFBundleDisplayName", data.get("CFBundleName", plist.stem)
                ),
                platform="ios",
                version=data.get("CFBundleShortVersionString", "0.0.0"),
                package_path=str(plist.resolve()),
            )
        except Exception as exc:
            raise RuntimeError(f"plist parse failed: {exc}") from exc
