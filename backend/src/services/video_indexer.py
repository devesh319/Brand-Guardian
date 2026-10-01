"""
Connector between Python and Azure Video Indexer
"""

import os
import time
import logging
import requests
import yt_dlp

from azure.identity import DefaultAzureCredential

logger = logging.getLogger("video-indexer")


class VideoIndexerService:
    def __init__(self):
        self.account_id = os.getenv("AZURE_VI_ACCOUNT_ID")
        self.location = os.getenv("AZURE_VI_LOCATION")
        self.subscription_id = os.getenv("AZURE_VI_SUBSCRIPTION_ID")
        self.resource_group = os.getenv("AZURE_VI_RESOURCE_GROUP")
        self.vi_name = os.getenv("AZURE_VI_NAME")
        self.credential = DefaultAzureCredential()

    def get_access_token(self):
        """
        Generates a ARM Access Token
        """
        try:
            token_object = self.credential.get_token("https://management.azure.com/")
            return token_object.token
        except Exception as e:
            logger.error(f"Failed to Get Azure RM Token: {str(e)}")

    def get_account_token(self, arm_access_token):
        """
        Exchanges the ARM token for Video Index Account
        """
        url = (
            f"https://management.azure.com/subscriptions/{self.subscription_id}"
            f"/resourceGroups/{self.resource_group}"
            f"/providers/Microsoft.VideoIndexer/accounts/{self.vi_name}"
            f"/generateAccessToken?api-version=2024-01-01"
        )

        headers = {"Authorization": f"Bearer {arm_access_token}"}
        payload = {"permissionType": "Contributor", "scope": "Account"}

        response = requests.post(url, headers=headers, json=payload)

        if response.status_code != 200:
            raise Exception(f"Failed to ge VI Account token : {response.text}")
        return response.json().get("accessToken")

    def download_youtube_video(
        self, video_url: str, output_path: str = "temp_audit_video.mp4"
    ):
        logger.info(f"Downloading Youtube Video: {video_url}")

        ydl_opts = {
            "format": "best",
            "outtmpl": output_path,
            "quiet": True,
            "no_warnings": False,
            "extractor_args": {"youtube": {"" "player_client": ["android", "web"]}},
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])
            logger.info("Download Complete!")
            return output_path
        except Exception as e:
            logger.error(f"YT Video Download Failed: {str(e)}")

    def upload_video(self, video_path, video_name):
        arm_token = self.get_access_token()
        vi_token = self.get_account_token(arm_token)

        api_url = f"https://api.videoindexer.ai/{self.location}/Accounts/{self.account_id}/Videos"

        params = {
            "accessToken": vi_token,
            "name": video_name,
            "privacy": "Private",
            "indexingPreset": "Default",
        }

        logger.info(f"Uploading file {video_path} to Azure Video Indexer")

        with open(video_path, "rb") as video_file:
            files = {"file": video_file}
            response = requests.post(
                url=api_url, params=params, files=files, timeout=120
            )

        if response.status_code != 200:
            logger.error(
                f"Failed to Upload file {video_path} to Azure Video Indexer: {response.text}"
            )
            raise Exception(
                f"Failed to Upload file {video_path} to Azure Video Indexer: {response.text}"
            )

        return response.json().get("id")

    def wait_for_processing(self, video_id):
        logger.info(f"Waiting for video {video_id} upload to Azure Video Indexer")

        i = 1
        while True:
            arm_token = self.get_access_token()
            vi_token = self.get_account_token(arm_token)

            api_url = f"https://api.videoindexer.ai/{self.location}/Accounts/{self.account_id}/Videos/{video_id}/Index"

            params = {"accessToken": vi_token}
            response = requests.get(api_url, params=params)
            data = response.json()

            state = data["state"]

            if state == "Processed":
                return data
            elif state == "Failed":
                raise Exception("Video Indexing failed in Azure")
            if state == "Quarantined":
                raise Exception(
                    "Video Quarantined (Copyright / Content Policy Violation)"
                )

            logger.info(f"State: {state}, .....waiting 30 sec now (Iteration {i})")
            i += 1
            time.sleep(30)

    def extract_data(self, vi_json):
        transcripts_lines = []
        ocr_lines = []

        for v in vi_json.get("videos", []):
            for insight in v.get("insights", {}).get("transcript", []):
                transcripts_lines.append(
                    insight.get(
                        "text",
                    )
                )

        for v in vi_json.get("videos", []):
            for insight in v.get("insights", {}).get("ocr", []):
                ocr_lines.append(
                    insight.get(
                        "text",
                    )
                )

        return {
            "transcript": " ".join(transcripts_lines),
            "ocr_text": ocr_lines,
            "video_metadata": {
                "duration": vi_json.get("summarizedIndights", {}).get("duration"),
                "platform": "youtube",
            },
        }
