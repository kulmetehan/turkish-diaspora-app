import { motion, PanInfo, useDragControls, useMotionValue } from "framer-motion";
import { ReactNode, useEffect, useState } from "react";

export type SnapPoint = "collapsed" | "half" | "full";

type Props = {
    open: boolean;
    snapPoint: SnapPoint;
    onSnapPointChange: (snapPoint: SnapPoint) => void;
    onClose: () => void;
    children: ReactNode;
};

const SNAP_POINTS = {
    collapsed: 96,
    half: 0.55, // 55vh
    full: 0.92, // 92vh
};

export default function BottomSheet({
    open,
    snapPoint,
    onSnapPointChange,
    onClose,
    children
}: Props) {
    const [isDragging, setIsDragging] = useState(false);
    const [currentHeight, setCurrentHeight] = useState(0);
    const dragControls = useDragControls();
    const y = useMotionValue(0);

    const getViewportHeight = () => (window.visualViewport?.height ?? window.innerHeight);

    // Calculate snap point heights
    const getSnapHeight = (snap: SnapPoint) => {
        if (snap === "collapsed") return SNAP_POINTS.collapsed;
        const viewportHeight = getViewportHeight();
        return snap === "half"
            ? viewportHeight * SNAP_POINTS.half
            : viewportHeight * SNAP_POINTS.full;
    };

    // Get current snap point based on height
    const getCurrentSnapPoint = (height: number): SnapPoint => {
        const viewportHeight = getViewportHeight();
        const collapsedHeight = SNAP_POINTS.collapsed;
        const halfHeight = viewportHeight * SNAP_POINTS.half;
        const fullHeight = viewportHeight * SNAP_POINTS.full;

        if (height <= collapsedHeight + 50) return "collapsed";
        if (height <= halfHeight + 50) return "half";
        return "full";
    };

    // Handle drag end
    const handleDragEnd = (event: any, info: PanInfo) => {
        setIsDragging(false);
        const velocity = info.velocity.y;
        const currentY = y.get();
        const viewportHeight = getViewportHeight();
        const currentHeight = viewportHeight - currentY;

        let targetSnap: SnapPoint;

        // Determine target snap point based on velocity and position
        if (velocity > 300) {
            // Fast downward swipe - go to collapsed
            targetSnap = "collapsed";
        } else if (velocity < -300) {
            // Fast upward swipe - go to full
            targetSnap = "full";
        } else {
            // Slow drag - snap to nearest based on current position
            const collapsedHeight = SNAP_POINTS.collapsed;
            const halfHeight = viewportHeight * SNAP_POINTS.half;
            const fullHeight = viewportHeight * SNAP_POINTS.full;

            // Find closest snap point
            const distances = {
                collapsed: Math.abs(currentHeight - collapsedHeight),
                half: Math.abs(currentHeight - halfHeight),
                full: Math.abs(currentHeight - fullHeight)
            };

            targetSnap = Object.entries(distances).reduce((a, b) =>
                distances[a[0] as SnapPoint] < distances[b[0] as SnapPoint] ? a : b
            )[0] as SnapPoint;
        }

        onSnapPointChange(targetSnap);
    };

    // Handle drag start
    const handleDragStart = () => {
        setIsDragging(true);
    };

    // Update height when snap point changes
    useEffect(() => {
        if (!isDragging) {
            const targetHeight = getSnapHeight(snapPoint);
            const viewportHeight = getViewportHeight();
            const targetY = viewportHeight - targetHeight;
            y.set(targetY);
            setCurrentHeight(targetHeight);
        }
    }, [snapPoint, isDragging, y]);

    // Recalculate on viewport resize/orientation changes
    useEffect(() => {
        const onResize = () => {
            const targetHeight = getSnapHeight(snapPoint);
            const vh = getViewportHeight();
            const targetY = vh - targetHeight;
            y.set(targetY);
            setCurrentHeight(targetHeight);
        };
        window.addEventListener('resize', onResize);
        window.addEventListener('orientationchange', onResize);
        // visualViewport for mobile address bar changes
        const vv = window.visualViewport;
        vv?.addEventListener('resize', onResize);
        return () => {
            window.removeEventListener('resize', onResize);
            window.removeEventListener('orientationchange', onResize);
            vv?.removeEventListener('resize', onResize);
        };
    }, [snapPoint, y]);

    if (!open) return null;

    return (
        <div className="fixed inset-0 z-50 pointer-events-none">
            {/* Overlay only at full, very light */}
            {snapPoint === 'full' && (
                <div
                    className="fixed inset-0 bg-black pointer-events-auto"
                    style={{ opacity: 0.04 }}
                    onClick={onClose}
                />
            )}

            {/* Bottom Sheet */}
            <motion.div
                className="fixed bottom-0 left-0 right-0 bg-background border-t border-border rounded-t-xl shadow-xl pointer-events-auto"
                style={{
                    y,
                    height: "100dvh",
                }}
                drag="y"
                dragControls={dragControls}
                dragListener={false}
                dragConstraints={{
                    top: getViewportHeight() - getSnapHeight('full'),
                    bottom: getViewportHeight() - getSnapHeight('collapsed')
                }}
                dragElastic={{ top: 0.1, bottom: 0.1 }}
                onDragStart={handleDragStart}
                onDragEnd={handleDragEnd}
                initial={{ y: getViewportHeight() - getSnapHeight("collapsed") }}
                animate={{
                    y: getViewportHeight() - getSnapHeight(snapPoint),
                }}
                transition={{
                    type: "spring",
                    damping: 25,
                    stiffness: 200,
                    duration: 0.4
                }}
            >
                {/* Drag handle */}
                <div
                    className="flex justify-center p-2 cursor-grab active:cursor-grabbing"
                    onPointerDown={(e) => dragControls.start(e)}
                >
                    <div className="w-8 h-1 bg-muted-foreground/30 rounded-full" />
                </div>

                {/* Content */}
                <div className="flex-1 overflow-hidden h-[calc(100dvh-24px)]">
                    {children}
                </div>
            </motion.div>
        </div>
    );
}
