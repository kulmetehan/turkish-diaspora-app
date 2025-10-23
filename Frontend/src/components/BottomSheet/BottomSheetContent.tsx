import { forwardRef } from "react";

type Props = React.PropsWithChildren<{
    className?: string;
}>;

const BottomSheetContent = forwardRef<HTMLDivElement, Props>(function BottomSheetContent({ className, children }, ref) {
    return (
        <div ref={ref} className={"tda-bs-content" + (className ? ` ${className}` : "")}>{children}</div>
    );
});

export default BottomSheetContent;


