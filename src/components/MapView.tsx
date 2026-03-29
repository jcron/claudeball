import { useMemo, useState, useCallback } from 'react';
import DeckGL from '@deck.gl/react';
import { HeatmapLayer } from '@deck.gl/aggregation-layers';
import { TileLayer } from '@deck.gl/geo-layers';
import { BitmapLayer, ScatterplotLayer } from '@deck.gl/layers';
import type { PickingInfo } from '@deck.gl/core';
import { useDataStore } from '../store/dataStore';
import { useFilterStore } from '../store/filterStore';
import { useFilteredPoints } from '../hooks/useFilteredPoints';
import type { WeightedPoint } from '../types/player';

const INITIAL_VIEW_STATE = {
  longitude: -30,
  latitude: 25,
  zoom: 2,
  pitch: 0,
  bearing: 0,
};

// Color ranges for each layer [r, g, b, a]
const BIRTH_COLORS: [number, number, number, number][] = [
  [0, 100, 200, 0],
  [0, 150, 255, 80],
  [0, 200, 255, 180],
  [100, 230, 255, 220],
  [200, 245, 255, 255],
];

const DEATH_COLORS: [number, number, number, number][] = [
  [150, 50, 0, 0],
  [220, 80, 0, 80],
  [255, 120, 20, 180],
  [255, 180, 60, 220],
  [255, 230, 140, 255],
];

const COLLEGE_COLORS: [number, number, number, number][] = [
  [0, 80, 20, 0],
  [0, 140, 40, 80],
  [0, 200, 80, 180],
  [80, 220, 120, 220],
  [180, 240, 180, 255],
];

const HIGHSCHOOL_COLORS: [number, number, number, number][] = [
  [80, 0, 150, 0],
  [130, 30, 200, 60],
  [170, 60, 230, 150],
  [210, 110, 240, 200],
  [240, 180, 255, 220],
];

const POPULATION_COLORS: [number, number, number, number][] = [
  [60, 60, 60, 0],
  [100, 100, 100, 40],
  [150, 150, 150, 100],
  [200, 200, 200, 160],
  [240, 240, 240, 200],
];

interface TooltipInfo {
  x: number;
  y: number;
  text: string;
}

export function MapView() {
  const { playerMap, populationPoints } = useDataStore();
  const { activeLayers } = useFilterStore();
  const { birth, death, college, highSchool } = useFilteredPoints();
  const [tooltip, setTooltip] = useState<TooltipInfo | null>(null);

  // Build scatter points for hover detection (birth layer only for perf)
  const scatterPoints = useMemo(() => {
    if (!activeLayers.has('birth')) return [];
    return birth.map((pt) => ({
      position: [pt[0], pt[1], 0] as [number, number, number],
      ...pt,
    }));
  }, [birth, activeLayers]);

  const onHover = useCallback(
    (info: PickingInfo) => {
      if (!info.coordinate || !info.object) {
        setTooltip(null);
        return;
      }
      const [lon, lat] = info.coordinate as [number, number];
      // Find nearest player
      let closest: { id: string; dist: number } | null = null;
      for (const pt of birth) {
        const d = Math.abs(pt[0] - lon) + Math.abs(pt[1] - lat);
        if (!closest || d < closest.dist) {
          closest = { id: '', dist: d };
          // find playerID for this point
        }
      }
      void closest; // used below via object
      const obj = info.object as { position: [number, number, number] };
      const [plon, plat] = obj.position;
      let playerName = '';
      let birthCity = '';
      for (const player of playerMap.values()) {
        if (
          player.birth?.lon != null &&
          player.birth?.lat != null &&
          Math.abs(player.birth.lon - plon) < 0.001 &&
          Math.abs(player.birth.lat - plat) < 0.001
        ) {
          playerName = player.name;
          birthCity = [player.birth.city, player.birth.country].filter(Boolean).join(', ');
          break;
        }
      }
      if (!playerName) {
        setTooltip(null);
        return;
      }
      setTooltip({
        x: info.x,
        y: info.y,
        text: `${playerName}${birthCity ? `\n${birthCity}` : ''}`,
      });
    },
    [birth, playerMap]
  );

  const baseTileLayer = useMemo(
    () =>
      new TileLayer({
        id: 'base-tiles',
        data: 'https://basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
        minZoom: 0,
        maxZoom: 19,
        tileSize: 256,
        renderSubLayers: (props) => {
          const { boundingBox } = props.tile;
          return new BitmapLayer(props, {
            data: undefined,
            image: props.data,
            bounds: [boundingBox[0][0], boundingBox[0][1], boundingBox[1][0], boundingBox[1][1]],
          });
        },
      }),
    []
  );

  const layers = useMemo(() => {
    const result = [baseTileLayer];

    if (activeLayers.has('population') && populationPoints.length > 0) {
      result.push(
        new HeatmapLayer({
          id: 'population',
          data: populationPoints,
          getPosition: (d: WeightedPoint) => [d[0], d[1]],
          getWeight: (d: WeightedPoint) => Math.log10(d[2] + 1),
          radiusPixels: 30,
          intensity: 1,
          threshold: 0.03,
          colorRange: POPULATION_COLORS,
          debounceTimeout: 100,
        }) as never
      );
    }

    if (activeLayers.has('death') && death.length > 0) {
      result.push(
        new HeatmapLayer({
          id: 'death',
          data: death,
          getPosition: (d: WeightedPoint) => [d[0], d[1]],
          getWeight: () => 1,
          radiusPixels: 40,
          intensity: 2,
          threshold: 0.03,
          colorRange: DEATH_COLORS,
          debounceTimeout: 100,
        }) as never
      );
    }

    if (activeLayers.has('college') && college.length > 0) {
      result.push(
        new HeatmapLayer({
          id: 'college',
          data: college,
          getPosition: (d: WeightedPoint) => [d[0], d[1]],
          getWeight: () => 1,
          radiusPixels: 40,
          intensity: 2,
          threshold: 0.03,
          colorRange: COLLEGE_COLORS,
          debounceTimeout: 100,
        }) as never
      );
    }

    if (activeLayers.has('highSchool') && highSchool.length > 0) {
      result.push(
        new HeatmapLayer({
          id: 'highSchool',
          data: highSchool,
          getPosition: (d: WeightedPoint) => [d[0], d[1]],
          getWeight: () => 1,
          radiusPixels: 40,
          intensity: 2,
          threshold: 0.03,
          colorRange: HIGHSCHOOL_COLORS,
          debounceTimeout: 100,
          opacity: 0.7,
        }) as never
      );
    }

    if (activeLayers.has('birth') && birth.length > 0) {
      result.push(
        new HeatmapLayer({
          id: 'birth',
          data: birth,
          getPosition: (d: WeightedPoint) => [d[0], d[1]],
          getWeight: () => 1,
          radiusPixels: 40,
          intensity: 2,
          threshold: 0.03,
          colorRange: BIRTH_COLORS,
          debounceTimeout: 100,
        }) as never
      );

      // Scatter layer for hover detection on birth points
      result.push(
        new ScatterplotLayer({
          id: 'birth-hover',
          data: scatterPoints,
          getPosition: (d) => d.position,
          getRadius: 20000,
          radiusMinPixels: 4,
          radiusMaxPixels: 20,
          getFillColor: [0, 0, 0, 0],
          pickable: true,
          onHover,
        }) as never
      );
    }

    return result;
  }, [
    baseTileLayer,
    activeLayers,
    birth,
    death,
    college,
    highSchool,
    populationPoints,
    scatterPoints,
    onHover,
  ]);

  return (
    <div className="relative w-full h-full">
      <DeckGL
        initialViewState={INITIAL_VIEW_STATE}
        controller
        layers={layers}
        style={{ width: '100%', height: '100%' }}
      />
      {tooltip && (
        <div
          className="absolute pointer-events-none bg-black/80 text-white text-xs rounded px-2 py-1 whitespace-pre"
          style={{ left: tooltip.x + 12, top: tooltip.y - 8 }}
        >
          {tooltip.text}
        </div>
      )}
    </div>
  );
}
