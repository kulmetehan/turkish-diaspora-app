import { motion, PanInfo, useMotionValue, useTransform } from "framer-motion";
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
    const y = useMotionValue(0);

    // Calculate snap point heights
    const getSnapHeight = (snap: SnapPoint) => {
        if (snap === "collapsed") return SNAP_POINTS.collapsed;
        const viewportHeight = window.innerHeight;
        return snap === "half"
            ? viewportHeight * SNAP_POINTS.half
            : viewportHeight * SNAP_POINTS.full;
    };

    // Get current snap point based on height
    const getCurrentSnapPoint = (height: number): SnapPoint => {
        const viewportHeight = window.innerHeight;
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
        const viewportHeight = window.innerHeight;
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
            const viewportHeight = window.innerHeight;
            const targetY = viewportHeight - targetHeight;
            y.set(targetY);
            setCurrentHeight(targetHeight);
        }
    }, [snapPoint, isDragging, y]);

    // Calculate opacity for overlay - much lighter overlay
    const overlayOpacity = useTransform(
        y,
        [window.innerHeight * 0.92, window.innerHeight * 0.55],
        [0.1, 0.02]
    );

    if (!open) return null;

    return (
        <div className="fixed inset-0 z-50">
            {/* Overlay */}
            <motion.div
                className="fixed inset-0 bg-black"
                style={{ opacity: overlayOpacity }}
                onClick={onClose}
            />

            {/* Bottom Sheet */}
            <motion.div
                className="fixed bottom-0 left-0 right-0 bg-background border-t border-border rounded-t-xl shadow-xl"
                style={{
                    y,
                    height: "100vh",
                }}
                drag="y"
                dragConstraints={{
                    top: window.innerHeight * 0.08, // Allow dragging to almost full screen
                    bottom: 0
                }}
                dragElastic={{ top: 0.1, bottom: 0.1 }}
                onDragStart={handleDragStart}
                onDragEnd={handleDragEnd}
                initial={{ y: window.innerHeight - getSnapHeight("collapsed") }}
                animate={{
                    y: window.innerHeight - getSnapHeight(snapPoint),
                }}
                transition={{
                    type: "spring",
                    damping: 25,
                    stiffness: 200,
                    duration: 0.4
                }}
            >
                {/* Drag handle */}
                <div className="flex justify-center p-2 cursor-grab active:cursor-grabbing">
                    <div className="w-8 h-1 bg-muted-foreground/30 rounded-full" />
                </div>

                {/* Content */}
                <div className="flex-1 overflow-hidden h-[calc(100vh-24px)]">
                    {children}
                </div>
            </motion.div>
        </div>
    );
}
