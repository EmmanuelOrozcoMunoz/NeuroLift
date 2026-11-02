import { describe, expect, it } from "vitest";

import { IMAGE_ACCEPT, isAcceptedImage } from "@/lib/images";

describe("isAcceptedImage", () => {
  it("acepta JPG, PNG, WEBP y HEIC por su tipo", () => {
    for (const type of ["image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"]) {
      expect(isAcceptedImage({ type, name: "foto" })).toBe(true);
    }
  });

  it("acepta un HEIC sin tipo MIME (lo habitual en Windows) por su extensión", () => {
    expect(isAcceptedImage({ type: "", name: "IMG_0001.HEIC" })).toBe(true);
    expect(isAcceptedImage({ type: "", name: "foto.heif" })).toBe(true);
  });

  it("rechaza GIF, SVG, AVIF y archivos que no son imágenes", () => {
    for (const type of ["image/gif", "image/svg+xml", "image/avif", "application/pdf", ""]) {
      expect(isAcceptedImage({ type, name: "archivo.bin" })).toBe(false);
    }
  });

  it("el selector de archivos ofrece HEIC", () => {
    expect(IMAGE_ACCEPT).toContain("image/heic");
    expect(IMAGE_ACCEPT).toContain(".heic");
  });
});
