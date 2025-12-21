// Onboarding Screen 1: Carousel with 3 slides
import ekleBg from "@/assets/ekle-bg.png";
import ekleIllustration from "@/assets/eklescherm.png";
import kesfetBg from "@/assets/kesfet-bg.png";
import kesfetIllustration from "@/assets/kesfet.jpg";
import yasaBg from "@/assets/yasa-bg.png";
import yasaIllustration from "@/assets/yasascherm.png";
import { Icon } from "@/components/Icon";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/ui/cn";
import { useRef, useState } from "react";
import { OnboardingProgress } from "./OnboardingProgress";

export interface OnboardingScreen1Props {
  onNext: () => void;
}

const slides = [
  {
    title: "Keşfet",
    body: "Zie waar Turkse ondernemers,\nevents en plekken zijn.",
    image: kesfetBg,
    illustration: kesfetIllustration,
  },
  {
    title: "Yaşa",
    body: "Bekijk lokaal nieuws,\npolls en wat er speelt in jouw omgeving.",
    image: yasaBg,
    illustration: yasaIllustration,
  },
  {
    title: "Ekle",
    body: "Zoek, reageer\nen voeg locaties toe.",
    image: ekleBg,
    illustration: ekleIllustration,
  },
];

export function OnboardingScreen1({ onNext }: OnboardingScreen1Props) {
  const [currentSlide, setCurrentSlide] = useState(0);
  const [touchStart, setTouchStart] = useState<number | null>(null);
  const [touchEnd, setTouchEnd] = useState<number | null>(null);
  const [mouseStart, setMouseStart] = useState<number | null>(null);
  const [mouseEnd, setMouseEnd] = useState<number | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

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
    if (currentSlide < slides.length - 1) {
      setCurrentSlide((prev) => prev + 1);
    } else {
      // Last slide - proceed to next screen
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
              {/* Mascotte avatar */}
              <img
                src={slide.image}
                alt={`${slide.title} mascotte`}
                className="h-20 w-20 md:h-32 md:w-32 object-contain mb-2 md:mb-4 flex-shrink-0"
              />

              {/* Progress dots */}
              <div className="mb-4 md:mb-6 flex-shrink-0">
                <OnboardingProgress current={currentSlide} total={slides.length} />
              </div>

              {/* Illustration image - shown between progress dots and title */}
              {slide.illustration && (
                <img
                  src={slide.illustration}
                  alt={`${slide.title} illustratie`}
                  className="h-48 md:h-[17.28rem] w-auto object-contain mb-2 md:mb-4 flex-shrink-0"
                />
              )}
              <h2 className="mb-2 md:mb-4 text-2xl md:text-3xl font-gilroy font-bold text-foreground flex-shrink-0">
                {slide.title}
              </h2>
              <p className="mb-4 md:mb-8 whitespace-pre-line text-base md:text-lg font-gilroy font-normal text-muted-foreground flex-shrink-0">
                {slide.body}
              </p>

              {/* Navigation buttons - Centered with content */}
              <div className="flex items-center justify-between gap-4 w-full max-w-md flex-shrink-0">
                {/* Previous button */}
                <Button
                  onClick={handlePrevious}
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
                  onClick={handleNext}
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




