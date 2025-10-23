import { stepSpring, type SpringConfig, type SpringState } from "@/lib/physics/spring";
import { useCallback, useEffect, useImperativeHandle, useRef, useState } from "react";

export type BottomSheetState = "collapsed" | "half" | "full";

export type BottomSheetRef = {
    snapTo: (state: BottomSheetState) => void;
    getState: () => BottomSheetState;
};

type Options = {
    initialState?: BottomSheetState;
    onStateChange?: (state: BottomSheetState) => void;
};

type SnapPoints = { collapsed: number; half: number; full: number };

function getViewportHeight(): number {
    return window.visualViewport?.height ?? window.innerHeight;
}

export function useBottomSheetController(ref: React.Ref<BottomSheetRef> | undefined, options: Options = {}) {
    const { initialState = "half", onStateChange } = options;

    const rootRef = useRef<HTMLDivElement | null>(null);
    const handleRef = useRef<HTMLDivElement | null>(null);
    const contentRef = useRef<HTMLDivElement | null>(null);

    const [state, setState] = useState<BottomSheetState>(initialState);
    const snapPointsRef = useRef<SnapPoints>({ collapsed: 64, half: Math.round(getViewportHeight() * 0.45), full: Math.round(getViewportHeight() * 0.94) });
    const yRef = useRef<number>(0); // translateY in px
    const targetYRef = useRef<number>(0);
    const pointerIdRef = useRef<number | null>(null);
    const isDraggingRef = useRef<boolean>(false);
    const lastYRef = useRef<number>(0);
    const lastTsRef = useRef<number>(0);
    const velocityRef = useRef<number>(0);
    const samplesRef = useRef<Array<{ t: number; y: number }>>([]);
    const rafRef = useRef<number | null>(null);
    const springingRef = useRef<boolean>(false);

    // Tuned for ~250–350ms settle on typical distances
    const springCfgRef = useRef<SpringConfig>({ stiffness: 120, damping: 28, tolerance: 0.5 });
    const springStateRef = useRef<SpringState>({ x: 0, v: 0 });
    const lastTargetStateRef = useRef<BottomSheetState | null>(null);
    const pendingDragRef = useRef<{ active: boolean; startY: number; pointerId: number } | null>(null);

    const applyTransform = useCallback((y: number) => {
        const el = rootRef.current;
        if (!el) return;
        el.style.transform = `translate3d(0, ${Math.max(0, y)}px, 0)`;
        yRef.current = y;
        // elevation interpolation (0 at full, 1 at collapsed)
        const { collapsed, full } = snapPointsRef.current;
        const yFull = getViewportHeight() - full;
        const yCollapsed = getViewportHeight() - collapsed;
        const t = Math.min(1, Math.max(0, (y - yFull) / Math.max(1, yCollapsed - yFull)));
        el.style.setProperty("--bs-elevation", `${t}`);
    }, []);

    const computeSnapPoints = useCallback((): SnapPoints => {
        const vh = getViewportHeight();
        return { collapsed: 64, half: Math.round(vh * 0.45), full: Math.round(vh * 0.94) };
    }, []);

    const stateToY = useCallback((s: BottomSheetState, sp: SnapPoints): number => {
        const vh = getViewportHeight();
        const h = s === "collapsed" ? sp.collapsed : s === "half" ? sp.half : sp.full;
        return Math.max(0, vh - h);
    }, []);

    const nearestStateForY = useCallback((y: number, sp: SnapPoints): BottomSheetState => {
        const vh = getViewportHeight();
        const d: Array<[BottomSheetState, number]> = [
            ["collapsed", Math.abs((vh - sp.collapsed) - y)],
            ["half", Math.abs((vh - sp.half) - y)],
            ["full", Math.abs((vh - sp.full) - y)],
        ];
        d.sort((a, b) => a[1] - b[1]);
        return d[0][0];
    }, []);

    const boundedY = useCallback((y: number): number => {
        const vh = getViewportHeight();
        const sp = snapPointsRef.current;
        const minY = vh - sp.full; // top bound
        const maxY = vh - sp.collapsed; // bottom bound
        if (y < minY) {
            const delta = y - minY; // negative
            return minY + delta / (1 + Math.abs(delta) / 120);
        }
        if (y > maxY) {
            const delta = y - maxY; // positive
            return maxY + delta / (1 + Math.abs(delta) / 120);
        }
        return y;
    }, []);

    const commitState = useCallback((next: BottomSheetState) => {
        setState(next);
        onStateChange?.(next);
        const lock = next === "full";
        document.documentElement.classList.toggle("bs-lock-scroll", lock);
    }, [onStateChange]);

    const stopRaf = useCallback(() => {
        if (rafRef.current != null) {
            cancelAnimationFrame(rafRef.current);
            rafRef.current = null;
        }
    }, []);

    const startSpringTo = useCallback((yTarget: number, nextState?: BottomSheetState) => {
        stopRaf();
        springingRef.current = true;
        targetYRef.current = yTarget;
        lastTargetStateRef.current = nextState ?? null;
        springStateRef.current = { x: yRef.current, v: velocityRef.current };
        const tick = (ts: number) => {
            if (!springingRef.current) return;
            if (!lastTsRef.current) lastTsRef.current = ts;
            const dt = Math.min(0.032, Math.max(0.008, (ts - lastTsRef.current) / 1000));
            lastTsRef.current = ts;
            const s = stepSpring(springStateRef.current, yTarget, springCfgRef.current, dt);
            springStateRef.current = s;
            applyTransform(s.x);
            if (s.v === 0 && s.x === yTarget) {
                springingRef.current = false;
                stopRaf();
                if (nextState) commitState(nextState);
                return;
            }
            rafRef.current = requestAnimationFrame(tick);
        };
        rafRef.current = requestAnimationFrame(tick);
    }, [applyTransform, commitState, stopRaf]);

    const chooseSnapFromRelease = useCallback((v: number, y: number): BottomSheetState => {
        const sp = snapPointsRef.current;
        const vh = getViewportHeight();
        const positions: Array<[BottomSheetState, number]> = [
            ["collapsed", vh - sp.collapsed],
            ["half", vh - sp.half],
            ["full", vh - sp.full],
        ];
        const threshold = 700; // px/s, tuned for mobile flings
        if (Math.abs(v) > threshold) {
            // Downward velocity -> toward collapsed; Upward -> toward full
            if (v > 0) {
                // find next greater y (closer to collapsed)
                const next = positions.filter(([, py]) => py >= y).sort((a, b) => a[1] - b[1])[0];
                return next ? next[0] : "collapsed";
            }
            const prev = positions.filter(([, py]) => py <= y).sort((a, b) => b[1] - a[1])[0];
            return prev ? prev[0] : "full";
        }
        // nearest by distance
        let best: BottomSheetState = "half";
        let bestD = Number.POSITIVE_INFINITY;
        for (const [s, py] of positions) {
            const d = Math.abs(py - y);
            if (d < bestD) {
                best = s; bestD = d;
            }
        }
        return best;
    }, []);

    const onPointerMove = useCallback((e: PointerEvent) => {
        if (!isDraggingRef.current) return;
        const root = rootRef.current;
        if (!root) return;
        if (pointerIdRef.current !== e.pointerId) return;

        const now = performance.now();
        const dy = e.clientY - lastYRef.current;

        // Scroll handoff
        const content = contentRef.current;
        const atFull = state === "full";
        if (content && atFull) {
            const scrollingDown = dy > 0;
            if (!scrollingDown) {
                // Upward gestures at full should scroll content
                return;
            }
            if (content.scrollTop > 0) {
                // Let content consume downward drag until it reaches top
                return;
            }
        }

        const yNew = boundedY(yRef.current + dy);
        applyTransform(yNew);

        samplesRef.current.push({ t: now, y: yNew });
        if (samplesRef.current.length > 5) samplesRef.current.shift();
        if (samplesRef.current.length >= 2) {
            const a = samplesRef.current[0];
            const b = samplesRef.current[samplesRef.current.length - 1];
            const dt = (b.t - a.t) / 1000;
            if (dt > 0) velocityRef.current = (b.y - a.y) / dt;
        }
        lastYRef.current = e.clientY;
    }, [applyTransform, boundedY, state]);

    const endDrag = useCallback(() => {
        if (!isDraggingRef.current) return;
        isDraggingRef.current = false;
        const v = velocityRef.current;
        const y = yRef.current;
        const next = chooseSnapFromRelease(v, y);
        const yTarget = stateToY(next, snapPointsRef.current);
        startSpringTo(yTarget, next);
        const root = rootRef.current;
        if (root && pointerIdRef.current != null) {
            try { root.releasePointerCapture(pointerIdRef.current); } catch { }
        }
        pointerIdRef.current = null;
        samplesRef.current = [];
    }, [chooseSnapFromRelease, startSpringTo, stateToY]);

    const onPointerUp = useCallback((e: PointerEvent) => {
        if (pointerIdRef.current !== e.pointerId) return;
        endDrag();
    }, [endDrag]);

    const startDrag = useCallback((clientY: number, pointerId: number) => {
        isDraggingRef.current = true;
        pointerIdRef.current = pointerId;
        lastYRef.current = clientY;
        samplesRef.current = [{ t: performance.now(), y: yRef.current }];
    }, []);

    const onRootPointerDown = useCallback((e: React.PointerEvent<HTMLDivElement>) => {
        const root = rootRef.current;
        const content = contentRef.current;
        if (!root) return;
        // Interrupt any ongoing spring immediately for user control
        springingRef.current = false;
        stopRaf();
        lastTsRef.current = 0;
        velocityRef.current = 0;
        // If pointer starts on content, delay capture decision until first move
        if (content && content.contains(e.target as Node)) {
            pendingDragRef.current = { active: true, startY: e.clientY, pointerId: e.pointerId };
            return;
        }
        root.setPointerCapture(e.pointerId);
        startDrag(e.clientY, e.pointerId);
    }, [state, startDrag, stopRaf]);

    const onHandlePointerDown = useCallback((e: React.PointerEvent<HTMLDivElement>) => {
        const root = rootRef.current;
        if (!root) return;
        // Interrupt spring for immediate control from handle
        springingRef.current = false;
        stopRaf();
        lastTsRef.current = 0;
        velocityRef.current = 0;
        root.setPointerCapture(e.pointerId);
        startDrag(e.clientY, e.pointerId);
    }, [startDrag, stopRaf]);

    // Decide on deferred capture when starting on content
    useEffect(() => {
        const decide = (e: PointerEvent) => {
            const pending = pendingDragRef.current;
            if (!pending || pending.pointerId !== e.pointerId) return;
            if (isDraggingRef.current) { pendingDragRef.current = null; return; }
            const content = contentRef.current;
            const root = rootRef.current;
            if (!content || !root) { pendingDragRef.current = null; return; }
            const dy = e.clientY - pending.startY;
            // If dragging downward and content is at top, take control
            if (dy > 4 && content.scrollTop === 0) {
                try { root.setPointerCapture(e.pointerId); } catch { }
                startDrag(e.clientY, e.pointerId);
                pendingDragRef.current = null;
            } else if (dy < -4) {
                // Upward drag: let content scroll
                pendingDragRef.current = null;
            }
        };
        const clearPending = () => { pendingDragRef.current = null; };
        window.addEventListener("pointermove", decide, { passive: true });
        window.addEventListener("pointerup", clearPending, { passive: true });
        window.addEventListener("pointercancel", clearPending, { passive: true });
        return () => {
            window.removeEventListener("pointermove", decide);
            window.removeEventListener("pointerup", clearPending);
            window.removeEventListener("pointercancel", clearPending);
        };
    }, [startDrag]);

    // Global listeners during drag
    useEffect(() => {
        const move = (e: PointerEvent) => onPointerMove(e);
        const up = (e: PointerEvent) => onPointerUp(e);
        window.addEventListener("pointermove", move, { passive: true });
        window.addEventListener("pointerup", up, { passive: true });
        window.addEventListener("pointercancel", up, { passive: true });
        return () => {
            window.removeEventListener("pointermove", move);
            window.removeEventListener("pointerup", up);
            window.removeEventListener("pointercancel", up);
        };
    }, [onPointerMove, onPointerUp]);

    // Resize/orientation changes
    useEffect(() => {
        const onResize = () => {
            const sp = computeSnapPoints();
            snapPointsRef.current = sp;
            const nextY = stateToY(state, sp);
            applyTransform(nextY);
        };
        const vv = window.visualViewport;
        window.addEventListener("resize", onResize);
        window.addEventListener("orientationchange", onResize);
        vv?.addEventListener("resize", onResize);
        return () => {
            window.removeEventListener("resize", onResize);
            window.removeEventListener("orientationchange", onResize);
            vv?.removeEventListener("resize", onResize);
        };
    }, [applyTransform, computeSnapPoints, state, stateToY]);

    // Initialize position
    useEffect(() => {
        const sp = computeSnapPoints();
        snapPointsRef.current = sp;
        const y0 = stateToY(state, sp);
        applyTransform(y0);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    // Imperative API
    const snapTo = useCallback((next: BottomSheetState) => {
        const sp = snapPointsRef.current;
        const yTarget = stateToY(next, sp);
        startSpringTo(yTarget, next);
    }, [startSpringTo, stateToY]);

    const getState = useCallback(() => state, [state]);

    useImperativeHandle(ref, () => ({ snapTo, getState }), [snapTo, getState]);

    return {
        refs: { rootRef, handleRef, contentRef },
        state,
        api: { snapTo, getState },
        debug: {
            getVelocity: () => velocityRef.current,
            getTargetState: () => lastTargetStateRef.current,
        },
        handlers: { onRootPointerDown, onHandlePointerDown },
    } as const;
}


