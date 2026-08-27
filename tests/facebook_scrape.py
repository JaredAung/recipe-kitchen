"""Sample Apify Facebook scrape payload used by unit tests."""

SCRAPE = {
    "facebookId": "123",
    "facebookUrl": "https://www.facebook.com/reel/123",
    "message": {"text": "  A recipe  "},
    "short_form_video_context": {
        "playback_video": {
            "videoDeliveryLegacyFields": {
                "browser_native_hd_url": "https://cdn.example/hd.mp4",
                "browser_native_sd_url": "https://cdn.example/sd.mp4",
            },
            "thumbnailImage": {"uri": "https://cdn.example/thumb.jpg"},
            "length_in_second": 12.5,
            "width": 1080,
            "height": 1920,
            "captions_url": "https://cdn.example/captions.vtt",
            "audio_availability": "AVAILABLE",
        },
        "video_owner": {"name": "Chef"},
        "track_title": "Original audio",
    },
}
