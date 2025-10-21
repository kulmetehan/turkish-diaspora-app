import { useEffect, useState } from "react";

/**
 * Hook for responsive breakpoint detection
 * @param query - CSS media query string (e.g., '(min-width: 1024px)')
 * @returns boolean indicating if the query matches
 */
export function useMediaQuery(query: string): boolean {
    const [matches, setMatches] = useState(false);

    useEffect(() => {
        const mql = window.matchMedia(query);
        setMatches(mql.matches);

        const handler = (e: MediaQueryListEvent) => setMatches(e.matches);
        mql.addEventListener('change', handler);

        return () => mql.removeEventListener('change', handler);
    }, [query]);

    return matches;
}
