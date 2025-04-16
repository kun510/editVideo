import os
import logging
import zipfile
from typing import List, Union
import numpy as np
from moviepy.editor import VideoFileClip, CompositeVideoClip, vfx, ImageClip

# Khắc phục lỗi PIL.Image.ANTIALIAS (nếu dùng ở nơi khác trong dự án)
try:
    from PIL import Image
    resample = Image.Resampling.LANCZOS
except AttributeError:
    resample = Image.ANTIALIAS  # cho Pillow cũ

def process_videos(main_video_path: str, secondary_video_path: str, output_path: str):
    target_width = 720
    target_height = 720
    target_size = (target_width, target_height)

    try:
        with VideoFileClip(main_video_path) as clip_main, VideoFileClip(secondary_video_path) as clip_secondary:

            min_duration = min(clip_main.duration, clip_secondary.duration)

            clip_main = clip_main.subclip(0, min_duration)
            clip_secondary = clip_secondary.subclip(0, min_duration)

            clip_secondary_resized = clip_secondary.resize(target_size)
            clip_main_resized = clip_main.resize(height=target_height)

            final_main_crop_width = target_width / 2

            if clip_main_resized.w < final_main_crop_width:
                clip_main_cropped = clip_main_resized
            else:
                clip_main_cropped = clip_main_resized.fx(
                    vfx.crop,
                    width=final_main_crop_width,
                    x_center=clip_main_resized.w / 2
                )

            def create_gradient_mask(size, fade_width=50):
                width, height = size
                mask = np.ones((height, width))
                for x in range(width - fade_width, width):
                    alpha = (width - x) / fade_width
                    mask[:, x] = alpha
                return mask

            mask = create_gradient_mask((int(final_main_crop_width), target_height))
            mask_clip = ImageClip(mask, ismask=True)

            clip_main_masked = clip_main_cropped.set_mask(mask_clip)
            clip_main_positioned = clip_main_masked.set_position(('left', 'center'))

            final_clip = CompositeVideoClip(
                [clip_secondary_resized, clip_main_positioned],
                size=target_size
            ).set_duration(min_duration)

            final_clip = final_clip.set_audio(clip_main.audio)

            output_fps = clip_main.fps if clip_main.fps else 24

            final_clip.write_videofile(
                output_path,
                codec="libx264",
                audio_codec="aac",
                fps=output_fps,
                preset='slow',
                bitrate="25000k"
            )

            # Đóng tất cả clip
            final_clip.close()
            mask_clip.close()

    except Exception as e:
        raise Exception(f"Lỗi khi xử lý video: {e}")


def process_multiple_videos(main_video_path: str, secondary_video_paths: List[str], output_dir: str) -> List[str]:
    output_files = []
    for i, secondary_path in enumerate(secondary_video_paths):
        output_filename = f"output_{i+1}.mp4"
        output_path = os.path.join(output_dir, output_filename)
        try:
            process_videos(main_video_path, secondary_path, output_path)
            output_files.append(output_path)
        except Exception as e:
            logging.error(f"Lỗi khi xử lý video {secondary_path}: {str(e)}")
            continue
    return output_files


def create_zip_file(output_files: List[str], zip_path: str):
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in output_files:
            filename = os.path.basename(file_path)
            zipf.write(file_path, filename)


def cleanup_files(*files: Union[str, List[str]]) -> None:
    """
    Clean up multiple files or lists of files
    Args:
        *files: Can be individual file paths or lists of file paths
    """
    for file_or_list in files:
        if isinstance(file_or_list, list):
            for file_path in file_or_list:
                _remove_file(file_path)
        else:
            _remove_file(file_or_list)


def _remove_file(file_path: str) -> None:
    """Helper function to remove a single file"""
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            logging.info(f"Đã xóa file: {file_path}")
        except Exception as e:
            logging.error(f"Lỗi khi xóa file {file_path}: {str(e)}")
