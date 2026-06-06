// Proxy module: replaces @pixi/core and @pixi/display for browser use.
// pixi-live2d-display imports from @pixi/core: Matrix, Texture, Transform, Point, ObservablePoint, utils
// pixi-live2d-display imports from @pixi/display: Container

// In browser, all of these are on window.PIXI

const P = typeof window !== 'undefined' ? window.PIXI : {};

export const Matrix = P.Matrix;
export const Texture = P.Texture;
export const Transform = P.Transform;
export const Point = P.Point;
export const ObservablePoint = P.ObservablePoint;
export const utils = P.utils;
export const Container = (P.display && P.display.Container) || P.Container;

// Other commonly used exports
export const settings = P.settings;
export const Ticker = P.Ticker;
export const Rectangle = P.Rectangle;
export const BaseTexture = P.BaseTexture;
export const RenderTexture = P.RenderTexture;
