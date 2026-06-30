import { UseQueryResult } from '@tanstack/react-query';
import { ReactNode } from 'react';
import { ErrorPanel } from './ErrorPanel';

export function QueryStatus({
  query,
  error,
  loading,
  children,
}: {
  query: UseQueryResult;
  error: string;
  /**
   * element to display when loading
   */
  loading: ReactNode;
  children: ReactNode;
}) {
  if (query.isError)
    return (
      <ErrorPanel retry={() => query.refetch()} isRetrying={query.isFetching}>
        {error}
      </ErrorPanel>
    );
  if (query.isLoading) return <>{loading}</>;
  if (query.isSuccess) return <>{children}</>;

  return <></>;
}
