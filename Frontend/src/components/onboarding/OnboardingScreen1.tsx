// Onboarding Screen 1: Carousel with 3 slides
import { Icon } from "@/components/Icon";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/ui/cn";
import { useRef, useState } from "react";
import { MascotteAvatar } from "./MascotteAvatar";
import { OnboardingProgress } from "./OnboardingProgress";

export interface OnboardingScreen1Props {
  onNext: () => void;
}

const slides = [
  {
    title: "Keşfet",
    body: "Zie waar Turkse ondernemers,\nevents en plekken zijn.",
  },
  {
    title: "Yaşa",
    body: "Bekijk lokaal nieuws,\npolls en wat er speelt in jouw omgeving.",
  },
  {
    title: "Ekle",
    body: "Zoek, reageer\nen voeg locaties toe.",
  },
];

export function OnboardingScreen1({ onNext }: OnboardingScreen1Props) {
  const [currentSlide, setCurrentSlide] = useState(0);
  const [touchStart, setTouchStart] = useState<number | null>(null);
  const [touchEnd, setTouchEnd] = useState<number | null>(null);
  const [mouseStart, setMouseStart] = useState<number | null>(null);
  const [mouseEnd, setMouseEnd] = useState<number | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // #region agent log
  if (typeof window !== 'undefined') {
    fetch('http://127.0.0.1:7242/ingest/37069a88-cc21-4ee6-bcd0-7b771fa9b5c4', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ location: 'OnboardingScreen1.tsx:35', message: 'Component render', data: { currentSlide }, timestamp: Date.now(), sessionId: 'debug-session', runId: 'run1', hypothesisId: 'A,B,C,D' }) }).catch(() => { });
  }
  // #endregion

  // Minimum swipe distance (in pixels)
  const minSwipeDistance = 50;

  // Touch handlers
  const onTouchStart = (e: React.TouchEvent) => {
    setTouchEnd(null);
    setTouchStart(e.targetTouches[0].clientX);
  };

  const onTouchMove = (e: React.TouchEvent) => {
    setTouchEnd(e.targetTouches[0].clientX);
  };

  const onTouchEnd = () => {
    if (!touchStart || !touchEnd) return;
    const distance = touchStart - touchEnd;
    const isLeftSwipe = distance > minSwipeDistance;
    const isRightSwipe = distance < -minSwipeDistance;

    if (isLeftSwipe && currentSlide < slides.length - 1) {
      setCurrentSlide(currentSlide + 1);
    }
    if (isRightSwipe && currentSlide > 0) {
      setCurrentSlide(currentSlide - 1);
    }
  };

  // Mouse handlers for drag
  const onMouseDown = (e: React.MouseEvent) => {
    setMouseEnd(null);
    setMouseStart(e.clientX);
  };

  const onMouseMove = (e: React.MouseEvent) => {
    if (mouseStart !== null) {
      setMouseEnd(e.clientX);
    }
  };

  const onMouseUp = () => {
    if (!mouseStart || !mouseEnd) return;
    const distance = mouseStart - mouseEnd;
    const isLeftSwipe = distance > minSwipeDistance;
    const isRightSwipe = distance < -minSwipeDistance;

    if (isLeftSwipe && currentSlide < slides.length - 1) {
      setCurrentSlide(currentSlide + 1);
    }
    if (isRightSwipe && currentSlide > 0) {
      setCurrentSlide(currentSlide - 1);
    }
    setMouseStart(null);
    setMouseEnd(null);
  };

  const handleNext = () => {
    // #region agent log
    if (typeof window !== 'undefined') {
      fetch('http://127.0.0.1:7242/ingest/37069a88-cc21-4ee6-bcd0-7b771fa9b5c4', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ location: 'OnboardingScreen1.tsx:91', message: 'handleNext called', data: { currentSlide, slidesLength: slides.length }, timestamp: Date.now(), sessionId: 'debug-session', runId: 'run1', hypothesisId: 'A' }) }).catch(() => { });
    }
    // #endregion
    if (currentSlide < slides.length - 1) {
      setCurrentSlide((prev) => {
        const next = prev + 1;
        // #region agent log
        if (typeof window !== 'undefined') {
          fetch('http://127.0.0.1:7242/ingest/37069a88-cc21-4ee6-bcd0-7b771fa9b5c4', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ location: 'OnboardingScreen1.tsx:95', message: 'Moving to next slide', data: { prev, next }, timestamp: Date.now(), sessionId: 'debug-session', runId: 'run1', hypothesisId: 'A' }) }).catch(() => { });
        }
        // #endregion
        return next;
      });
    } else {
      // Last slide - proceed to next screen
      // #region agent log
      if (typeof window !== 'undefined') {
        fetch('http://127.0.0.1:7242/ingest/37069a88-cc21-4ee6-bcd0-7b771fa9b5c4', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ location: 'OnboardingScreen1.tsx:99', message: 'Calling onNext', data: { currentSlide }, timestamp: Date.now(), sessionId: 'debug-session', runId: 'run1', hypothesisId: 'A' }) }).catch(() => { });
      }
      // #endregion
      onNext();
    }
  };

  const handlePrevious = () => {
    if (currentSlide > 0) {
      setCurrentSlide((prev) => prev - 1);
    }
  };


  return (
    <div className="fixed inset-0 z-[100] bg-background" style={{ height: '100vh', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* Header with mascotte */}
      <div className="flex-shrink-0 flex flex-col items-center justify-center px-6 pt-12 pb-6">
        <MascotteAvatar size="lg" className="mb-4" />
        <OnboardingProgress current={currentSlide} total={slides.length} />
      </div>

      {/* Carousel container - Show only active slide */}
      <div
        ref={containerRef}
        className="relative flex-1 overflow-hidden"
        style={{
          zIndex: 1,
          minHeight: 0
        }}
        onTouchStart={onTouchStart}
        onTouchMove={onTouchMove}
        onTouchEnd={onTouchEnd}
        onMouseDown={onMouseDown}
        onMouseMove={onMouseMove}
        onMouseUp={onMouseUp}
        onMouseLeave={onMouseUp}
      >
        {/* #region agent log */}
        {typeof window !== 'undefined' && containerRef.current && (() => {
          const rect = containerRef.current.getBoundingClientRect();
          fetch('http://127.0.0.1:7242/ingest/37069a88-cc21-4ee6-bcd0-7b771fa9b5c4', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ location: 'OnboardingScreen1.tsx:128', message: 'Carousel container dimensions', data: { top: rect.top, bottom: rect.bottom, height: rect.height }, timestamp: Date.now(), sessionId: 'debug-session', runId: 'run1', hypothesisId: 'C' }) }).catch(() => { });
          return null;
        })()}
        {/* #endregion */}
        <div className="relative h-full w-full">
          {slides.map((slide, index) => (
            <div
              key={index}
              data-slide-index={index}
              className={cn(
                "absolute inset-0 flex flex-col items-center justify-center px-6 text-center transition-opacity duration-300",
                index === currentSlide ? "opacity-100 z-10" : "opacity-0 z-0 pointer-events-none"
              )}
              style={{ pointerEvents: index === currentSlide ? 'auto' : 'none' }}
            >
              {/* #region agent log */}
              {typeof window !== 'undefined' && index === currentSlide && (() => {
                const slideEl = document.querySelector(`[data-slide-index="${index}"]`);
                if (slideEl) {
                  const rect = (slideEl as HTMLElement).getBoundingClientRect();
                  fetch('http://127.0.0.1:7242/ingest/37069a88-cc21-4ee6-bcd0-7b771fa9b5c4', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ location: 'OnboardingScreen1.tsx:137', message: 'Active slide dimensions', data: { index, top: rect.top, bottom: rect.bottom, height: rect.height, zIndex: window.getComputedStyle(slideEl as Element).zIndex }, timestamp: Date.now(), sessionId: 'debug-session', runId: 'run1', hypothesisId: 'A,B' }) }).catch(() => { });
                }
                return null;
              })()}
              {/* #endregion */}
              <h2 className="mb-4 text-3xl font-gilroy font-bold text-foreground">
                {slide.title}
              </h2>
              <p className="mb-8 whitespace-pre-line text-lg font-gilroy font-normal text-muted-foreground">
                {slide.body}
              </p>

              {/* Navigation buttons - Directly under the text */}
              <div className="flex items-center justify-between gap-4 w-full max-w-md mt-6">
                {/* Previous button */}
                <Button
                  onClick={() => {
                    // #region agent log
                    if (typeof window !== 'undefined') {
                      fetch('http://127.0.0.1:7242/ingest/37069a88-cc21-4ee6-bcd0-7b771fa9b5c4', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ location: 'OnboardingScreen1.tsx:160', message: 'Previous button clicked', data: { currentSlide }, timestamp: Date.now(), sessionId: 'debug-session', runId: 'run1', hypothesisId: 'A' }) }).catch(() => { });
                    }
                    // #endregion
                    handlePrevious();
                  }}
                  variant="outline"
                  size="lg"
                  disabled={currentSlide === 0}
                  className="flex items-center gap-2 font-gilroy min-w-[100px]"
                  aria-label="Vorige"
                >
                  <Icon name="ChevronLeft" sizeRem={1.25} />
                  Vorige
                </Button>

                {/* Progress dots */}
                <div className="flex gap-2">
                  {slides.map((_, slideIndex) => (
                    <button
                      key={slideIndex}
                      onClick={() => setCurrentSlide(slideIndex)}
                      className={cn(
                        "h-2 w-2 rounded-full transition-all cursor-pointer",
                        slideIndex === currentSlide
                          ? "bg-primary scale-125"
                          : "bg-muted-foreground/30 hover:bg-muted-foreground/50"
                      )}
                      aria-label={`Ga naar slide ${slideIndex + 1}`}
                    />
                  ))}
                </div>

                {/* Next/Complete button */}
                <Button
                  onClick={() => {
                    // #region agent log
                    if (typeof window !== 'undefined') {
                      fetch('http://127.0.0.1:7242/ingest/37069a88-cc21-4ee6-bcd0-7b771fa9b5c4', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ location: 'OnboardingScreen1.tsx:190', message: 'Next button clicked', data: { currentSlide, isLast: currentSlide === slides.length - 1 }, timestamp: Date.now(), sessionId: 'debug-session', runId: 'run1', hypothesisId: 'A' }) }).catch(() => { });
                    }
                    // #endregion
                    handleNext();
                  }}
                  size="lg"
                  variant="default"
                  className="flex items-center gap-2 font-gilroy min-w-[100px]"
                  aria-label={currentSlide === slides.length - 1 ? "Oké, duidelijk" : "Volgende"}
                >
                  {currentSlide === slides.length - 1 ? (
                    "Oké, duidelijk"
                  ) : (
                    <>
                      Volgende
                      <Icon name="ChevronRight" sizeRem={1.25} />
                    </>
                  )}
                </Button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
