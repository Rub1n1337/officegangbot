import { useColorModeValue, useToken, Box } from '@chakra-ui/react';
import { deepmerge } from 'deepmerge-ts';
import dynamic from 'next/dynamic';
import { useEffect, useRef, useState } from 'react';
import type { Props as ChartProps } from 'react-apexcharts';

const Chart = dynamic(() => import('react-apexcharts'), { ssr: false });

export function StyledChart(props: ChartProps) {
  const theme = useColorModeValue('light', 'dark');
  const [textColorPrimary, textColorSecondary] = useToken('colors', [
    'TextPrimary',
    'TextSecondary',
  ]);

  // Don't mount the chart until its container actually has a width. ApexCharts
  // measures the parent on mount; when that width is 0 (the first client paint,
  // a not-yet-laid-out SimpleGrid column, or a device-emulation viewport) every
  // downstream length is computed from zero and comes out NaN — the console
  // then fills with "<svg> width NaN", "<foreignObject> width NaN" and
  // "translate(NaN, 0)". Latch to true on the first positive width and stay
  // mounted; a transient later 0 (during a resize) doesn't unmount it.
  const wrapRef = useRef<HTMLDivElement>(null);
  const [ready, setReady] = useState(false);
  useEffect(() => {
    const el = wrapRef.current;
    if (!el || ready) return;
    if (el.offsetWidth > 0) {
      setReady(true);
      return;
    }
    const ro = new ResizeObserver((entries) => {
      if (entries[0]?.contentRect.width) setReady(true);
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, [ready]);

  const options: ApexCharts.ApexOptions = {
    // Without a theme mode + transparent background the chart keeps a white
    // canvas in dark mode — most visible on the heatmap, whose zero-value cells
    // shade toward white and lit up as a bright block on the dark card.
    theme: { mode: theme },
    chart: {
      background: 'transparent',
      // The entry/resize animation runs on setTimeout frames that interpolate
      // geometry — the exact frames that emitted "translate(NaN, 0)" while a
      // dimension was still resolving. The dashboard doesn't need it, and off
      // it means one clean paint instead of a stream of transient bad frames.
      animations: { enabled: false },
      toolbar: {
        show: false,
      },
      dropShadow: {
        enabled: true,
        top: 13,
        left: 0,
        blur: 10,
        opacity: 0.1,
        color: '#4318FF',
      },
    },
    tooltip: {
      fillSeriesColor: false,
      theme: theme,
    },
    markers: {
      size: 0,
      colors: textColorPrimary,
      strokeColors: '#7551FF',
      strokeWidth: 3,
      strokeOpacity: 0.9,
      strokeDashArray: 0,
      fillOpacity: 1,
      discrete: [],
      shape: 'circle',
      offsetX: 0,
      offsetY: 0,
      showNullDataPoints: true,
    },
    stroke: {
      curve: 'smooth',
    },
    legend: {
      labels: {
        colors: textColorSecondary,
      },
    },
    grid: {
      show: false,
    },
    yaxis: {
      labels: {
        style: {
          colors: textColorSecondary,
        },
      },
    },
    xaxis: {
      labels: {
        style: {
          colors: textColorSecondary,
          fontSize: '12px',
          fontWeight: '500',
        },
      },
    },
  };

  // Reserve the chart's height so gating the mount doesn't shift the layout.
  const minHeight = typeof props.height === 'number' ? props.height : undefined;

  return (
    <Box ref={wrapRef} w="100%" minH={minHeight ? `${minHeight}px` : undefined}>
      {ready && <Chart {...props} options={deepmerge(options, props.options)} />}
    </Box>
  );
}
