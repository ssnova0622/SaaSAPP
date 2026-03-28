### Plan confirmed — next steps

Thanks for confirming. I will proceed with the plan to ensure tenant changes reflect across all pages.

What you can expect:
- Pages already using `useEffectiveTenant` will continue to refetch on tenant change.
- I will align any remaining outliers (e.g., legacy `useTenant` usages like Store Orders) and add lightweight request guards to avoid stale updates on rapid switches.
- The single tenant selector remains only at the top‑left in the AppBar; non‑super see a read‑only badge.

I’ll report back once the verification and any minimal fixes are completed.