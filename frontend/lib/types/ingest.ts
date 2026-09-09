export type IngestMedia = {
  video_id: string;
  source_url: string;
  caption: string;
  duration: number;
  width: number;
  height: number;
  audio_available: string;
  creator_name: string;
  audio_title: string;
};

export type IngestResult = {
  media: IngestMedia;
  video: string;
  thumbnail: string;
  subtitle_text: string;
};
