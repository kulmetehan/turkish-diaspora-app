import { forwardRef, useEffect, useMemo } from "react";
import BottomSheetContent from "./BottomSheet/BottomSheetContent";
import "./BottomSheet/bottomSheet.css";
import { useBottomSheetController, type BottomSheetState, type BottomSheetRef as ControllerRef } from "./BottomSheet/useBottomSheetController";

export type SnapPoint = BottomSheetState;

type Props = React.PropsWithChildren<{
    open?: boolean;
    snapPoint?: SnapPoint;
    onSnapPointChange?: (snapPoint: SnapPoint) => void;
    onClose?: () => void;
    onStateChange?: (s: SnapPoint) => void;
}>;

const BottomSheet = forwardRef<ControllerRef, Props>(function BottomSheet({ open = true, snapPoint, onSnapPointChange, onClose, onStateChange, children }, ref) {
    const controller = useBottomSheetController(ref as any, {
        initialState: snapPoint ?? "half", onStateChange: (s) => {
            onSnapPointChange?.(s);
            onStateChange?.(s);
        }
    });

    const { refs, state, api, handlers, debug } = controller as any;

    // Attach controller for playground debug
    useEffect(() => {
        if (!ref || typeof ref === "function") return;
        try { (ref as any).current && ((ref as any).current._controller = controller); } catch { }
    }, [controller, ref]);

    // Controlled prop: when parent requests a different snap, follow
    useEffect(() => {
        if (!snapPoint) return;
        if (snapPoint !== state) {
            api.snapTo(snapPoint);
        }
    }, [api, snapPoint, state]);

    const ariaExpanded = useMemo(() => state !== "collapsed", [state]);
    if (!open) return null;

    return (
        <div className="fixed inset-0 z-50 pointer-events-none">
            {/* Backdrop visible only at full; clicking sends to half */}
            <div
                className={"tda-bs-backdrop" + (state === "full" ? " visible" : "")}
                onClick={() => api.snapTo("half")}
                aria-hidden
            />
            <div
                ref={refs.rootRef}
                className="tda-bs-root bg-background border-t border-border pointer-events-auto"
                onPointerDown={handlers.onRootPointerDown}
                role="dialog"
                aria-modal="false"
            >
                <div
                    ref={refs.handleRef}
                    className="tda-bs-handle flex justify-center p-2"
                    role="button"
                    aria-expanded={ariaExpanded}
                    tabIndex={0}
                    onPointerDown={handlers.onHandlePointerDown}
                    onKeyDown={(e) => {
                        if (e.key === "Escape") {
                            if (state === "full") api.snapTo("half");
                            else if (state === "half") api.snapTo("collapsed");
                            else onClose?.();
                        } else if (e.key === "Enter" || e.key === " ") {
                            if (state === "collapsed") api.snapTo("half");
                            else if (state === "half") api.snapTo("full");
                            else api.snapTo("half");
                        }
                    }}
                >
                    <div className="tda-bs-handle-bar" />
                </div>
                <BottomSheetContent ref={refs.contentRef}>
                    {children}
                </BottomSheetContent>
            </div>
        </div>
    );
});

export type BottomSheetRef = ControllerRef;
export default BottomSheet;
