export type SpringState = { x: number; v: number };

export type SpringConfig = {
    stiffness: number;
    damping: number;
    tolerance?: number;
};

export function stepSpring(state: SpringState, target: number, cfg: SpringConfig, dt: number): SpringState {
    const displacement = state.x - target;
    const springForce = -cfg.stiffness * displacement;
    const dampingForce = -cfg.damping * state.v;
    const accel = springForce + dampingForce; // mass = 1
    const v = state.v + accel * dt;
    const x = state.x + v * dt;
    const tol = cfg.tolerance ?? 0.5;
    if (Math.abs(v) < 0.02 && Math.abs(displacement) < tol) {
        return { x: target, v: 0 };
    }
    return { x, v };
}

export function estimateDurationPx(rangePx: number, cfg: SpringConfig): number {
    // Rough heuristic to predict settle time for tuning; not used for animation.
    const k = cfg.stiffness;
    const c = cfg.damping;
    const zeta = c / (2 * Math.sqrt(k));
    if (zeta >= 1) {
        // overdamped approximation
        return 0.35 + Math.min(0.5, rangePx / 3000);
    }
    // under/critically damped approximation
    return 0.28 + Math.min(0.5, rangePx / 4000);
}


