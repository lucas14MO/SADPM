interface ErrorBannerProps {
  message: string;
  onRetry: () => void;
}

export default function ErrorBanner({ message, onRetry }: ErrorBannerProps) {
  return (
    <div className="absolute inset-x-3 top-16 z-[1100] flex items-center justify-between gap-3 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700 shadow-md sm:inset-x-auto sm:right-3 sm:top-3 sm:w-80">
      <span>{message}</span>
      <button type="button" onClick={onRetry} className="font-semibold underline">
        Reintentar
      </button>
    </div>
  );
}
