import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import NewsAIDiagnosticsPanel from "@/components/admin/NewsAIDiagnosticsPanel";

vi.mock("@/lib/apiAdmin", () => ({
    listAILogs: vi.fn(),
    getAILogDetail: vi.fn(),
}));

vi.mock("sonner", () => ({
    toast: {
        error: vi.fn(),
    },
}));

const mockListAILogs = vi.mocked((await import("@/lib/apiAdmin")).listAILogs);
const mockGetAILogDetail = vi.mocked((await import("@/lib/apiAdmin")).getAILogDetail);

const baseResponse = {
    items: [
        {
            id: 1,
            location_id: null,
            news_id: 42,
            action_type: "news.classify",
            model_used: "gpt",
            confidence_score: 0.9,
            category: "news",
            created_at: new Date().toISOString(),
            validated_output: { category: "news" },
            is_success: true,
            error_message: null,
            explanation: "Classified as diaspora news.",
            news_source_key: "anp",
            news_source_name: "ANP",
        },
    ],
    total: 1,
    limit: 20,
    offset: 0,
};

describe("NewsAIDiagnosticsPanel", () => {
    beforeEach(() => {
        mockListAILogs.mockResolvedValue(baseResponse);
        mockGetAILogDetail.mockResolvedValue({
            id: 1,
            location_id: null,
            news_id: 42,
            action_type: "news.classify",
            model_used: "gpt",
            prompt: { system: "test" },
            raw_response: { raw: "ok" },
            validated_output: { category: "news" },
            is_success: true,
            error_message: null,
            created_at: new Date().toISOString(),
            news_source_key: "anp",
            news_source_name: "ANP",
            news_title: "Sample title",
        });
    });

    afterEach(() => {
        vi.clearAllMocks();
    });

    it("loads news logs by default with news_only=true", async () => {
        render(<NewsAIDiagnosticsPanel />);
        await waitFor(() => expect(mockListAILogs).toHaveBeenCalled());
        expect(mockListAILogs).toHaveBeenCalledWith(
            expect.objectContaining({ news_only: true, offset: 0, limit: 20 }),
        );
    });

    it("switches to location mode without news filters", async () => {
        render(<NewsAIDiagnosticsPanel />);
        await waitFor(() => expect(mockListAILogs).toHaveBeenCalledTimes(1));
        mockListAILogs.mockResolvedValueOnce({
            ...baseResponse,
            items: [
                {
                    ...baseResponse.items[0],
                    news_id: null,
                    location_id: 99,
                    action_type: "verify_locations.classified",
                },
            ],
        });
        const locationButtons = screen.getAllByRole("button", { name: /location logs/i });
        fireEvent.click(locationButtons[0]);
        await waitFor(() => expect(mockListAILogs).toHaveBeenCalledTimes(2));
        expect(mockListAILogs).toHaveBeenLastCalledWith(
            expect.objectContaining({ news_only: false }),
        );
    });

    it("opens detail dialog when selecting a log", async () => {
        render(<NewsAIDiagnosticsPanel />);
        await waitFor(() => expect(mockListAILogs).toHaveBeenCalled());
        const detailButtons = await screen.findAllByRole("button", { name: /view details/i });
        fireEvent.click(detailButtons[0]);
        await waitFor(() => expect(mockGetAILogDetail).toHaveBeenCalledWith(1));
        expect(await screen.findByText(/Sample title/)).toBeTruthy();
        const explanationMatches = await screen.findAllByText(/Classified as diaspora news/i);
        expect(explanationMatches[0]).toBeTruthy();
    });
});

