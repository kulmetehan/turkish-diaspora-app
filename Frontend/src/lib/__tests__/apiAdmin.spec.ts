import { describe, expect, it, beforeEach, vi } from "vitest";

import { authFetch } from "@/lib/api";
import {
    getAILogDetail,
    listAILogs,
    listEventCandidatesAdmin,
    publishEventCandidateAdmin,
    rejectEventCandidateAdmin,
    verifyEventCandidateAdmin,
} from "@/lib/apiAdmin";

vi.mock("@/lib/api", () => ({
    authFetch: vi.fn(),
}));

const mockAuthFetch = authFetch as unknown as ReturnType<typeof vi.fn>;

describe("apiAdmin AI logs client", () => {
    beforeEach(() => {
        mockAuthFetch.mockReset();
    });

    it("serializes news filters when listing AI logs", async () => {
        mockAuthFetch.mockResolvedValue({ items: [], total: 0, limit: 20, offset: 0 });

        await listAILogs({
            news_only: true,
            news_id: 7,
            source_key: "anp",
            source_name: "ANP",
            limit: 10,
            offset: 5,
        });

        expect(mockAuthFetch).toHaveBeenCalledWith(
            "/api/v1/admin/ai/logs?news_only=true&news_id=7&source_key=anp&source_name=ANP&limit=10&offset=5",
        );
    });

    it("fetches AI log detail for a single id", async () => {
        const sample = { id: 1 };
        mockAuthFetch.mockResolvedValue(sample);

        const result = await getAILogDetail(123);
        expect(mockAuthFetch).toHaveBeenCalledWith("/api/v1/admin/ai/logs/123");
        expect(result).toBe(sample);
    });
});

describe("apiAdmin event candidates client", () => {
    beforeEach(() => {
        mockAuthFetch.mockReset();
    });

    it("serializes filters when listing event candidates", async () => {
        mockAuthFetch.mockResolvedValue({ items: [], total: 0, limit: 50, offset: 0 });

        await listEventCandidatesAdmin({
            state: "candidate",
            sourceKey: "rotterdam_culture",
            search: "meet",
            limit: 25,
            offset: 50,
        });

        expect(mockAuthFetch).toHaveBeenCalledWith(
            "/api/v1/admin/events/candidates?state=candidate&source_key=rotterdam_culture&search=meet&limit=25&offset=50",
        );
    });

    it("posts to verify endpoint", async () => {
        mockAuthFetch.mockResolvedValue({});
        await verifyEventCandidateAdmin(5);
        expect(mockAuthFetch).toHaveBeenCalledWith(
            "/api/v1/admin/events/candidates/5/verify",
            { method: "POST" },
        );
    });

    it("posts to publish endpoint", async () => {
        mockAuthFetch.mockResolvedValue({});
        await publishEventCandidateAdmin(9);
        expect(mockAuthFetch).toHaveBeenCalledWith(
            "/api/v1/admin/events/candidates/9/publish",
            { method: "POST" },
        );
    });

    it("posts to reject endpoint", async () => {
        mockAuthFetch.mockResolvedValue({});
        await rejectEventCandidateAdmin(2);
        expect(mockAuthFetch).toHaveBeenCalledWith(
            "/api/v1/admin/events/candidates/2/reject",
            { method: "POST" },
        );
    });
});


