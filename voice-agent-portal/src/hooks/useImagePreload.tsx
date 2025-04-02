import { useEffect, useState } from "react";

/**
 * A custom hook that preloads an image to ensure it's cached by the browser
 *
 * @param src The source URL of the image to preload
 * @returns Object containing loading state and any error that occurred
 */
const useImagePreload = (src: string) => {
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const img = new Image();

    img.onload = () => {
      setLoaded(true);
    };

    img.onerror = () => {
      setError(`Failed to load image: ${src}`);
      setLoaded(true); // Consider it "loaded" even on error to prevent blocking
    };

    img.src = src;

    // If the image is already cached, the onload event might not fire
    if (img.complete) {
      setLoaded(true);
    }

    return () => {
      // Clean up
      img.onload = null;
      img.onerror = null;
    };
  }, [src]);

  return { loaded, error };
};

export default useImagePreload;
