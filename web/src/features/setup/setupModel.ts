export const COURT_CORNER_ORDER = ["far_left", "far_right", "near_right", "near_left"] as const;

export type CourtCornerName = (typeof COURT_CORNER_ORDER)[number];
export interface NormalizedPoint { x: number; y: number }
export type CourtCorners = Partial<Record<CourtCornerName, NormalizedPoint>>;

interface PointerLike { clientX: number; clientY: number }
interface RectLike { left: number; top: number; width: number; height: number }

function clamp(value: number): number {
  return Math.max(0, Math.min(1, value));
}

export function normalizedPointFromPointer(pointer: PointerLike, rect: RectLike): NormalizedPoint {
  return {
    x: clamp((pointer.clientX - rect.left) / Math.max(rect.width, 1)),
    y: clamp((pointer.clientY - rect.top) / Math.max(rect.height, 1)),
  };
}

export function canSubmitSetup(
  learnerTrackId: string,
  partnerTrackId: string,
  corners: CourtCorners,
): boolean {
  return Boolean(
    learnerTrackId
    && partnerTrackId
    && learnerTrackId !== partnerTrackId
    && COURT_CORNER_ORDER.every((name) => corners[name]),
  );
}

export function nextCourtCorner(corners: CourtCorners): CourtCornerName | null {
  return COURT_CORNER_ORDER.find((name) => !corners[name]) ?? null;
}
