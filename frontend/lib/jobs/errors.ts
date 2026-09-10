export class ValidationError extends Error {
  constructor(
    readonly loc: Array<string | number>,
    message: string,
  ) {
    super(message);
    this.name = "ValidationError";
  }
}

export class RateLimitError extends Error {
  readonly status = 429;

  constructor(message = "You already have extracts in progress. Wait for them to finish.") {
    super(message);
    this.name = "RateLimitError";
  }
}

export class EmptyRecipeError extends Error {
  readonly status = 400;

  constructor() {
    super("Provide a caption, subtitles, or an ingested video path.");
    this.name = "EmptyRecipeError";
  }
}
