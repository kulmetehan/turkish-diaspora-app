import BottomSheet, { type BottomSheetRef, type SnapPoint } from "@/components/BottomSheet";
import { useEffect, useRef, useState } from "react";

export default function BottomSheetPlayground() {
    const ref = useRef<BottomSheetRef>(null);
    const [state, setState] = useState<SnapPoint>("half");
    const [velocity, setVelocity] = useState(0);
    const [target, setTarget] = useState<SnapPoint | null>(null);

    // Poll velocity/target for debug overlay
    useEffect(() => {
        let raf: number;
        const tick = () => {
            // @ts-expect-error internal debug
            const v = (ref.current as any)?._controller?.debug?.getVelocity?.() ?? 0;
            // @ts-expect-error internal debug
            const t = (ref.current as any)?._controller?.debug?.getTargetState?.() ?? null;
            setVelocity(Math.round(v));
            setTarget(t);
            raf = requestAnimationFrame(tick);
        };
        raf = requestAnimationFrame(tick);
        return () => cancelAnimationFrame(raf);
    }, []);

    const longList = Array.from({ length: 100 }, (_, i) => `Item ${i + 1}`);

    return (
        <div className="h-[100dvh] w-full">
            <div className="p-3 flex gap-2 text-sm">
                <button className="px-3 py-2 rounded border" onClick={() => ref.current?.snapTo("collapsed")}>Collapsed</button>
                <button className="px-3 py-2 rounded border" onClick={() => ref.current?.snapTo("half")}>Half</button>
                <button className="px-3 py-2 rounded border" onClick={() => ref.current?.snapTo("full")}>Full</button>
                <div className="ml-auto">velocity: {velocity}px/s · target: {target ?? "-"}</div>
            </div>

            <BottomSheet ref={ref} snapPoint={state} onSnapPointChange={setState}>
                <div className="p-3 border-b">Debug state: {state}</div>
                <ul>
                    {longList.map((x) => (
                        <li key={x} className="px-3 py-2 border-b">{x}</li>
                    ))}
                </ul>
            </BottomSheet>
        </div>
    );
}


