library(dplyr)

# --- 1. 地点データ読み込み / 絞り込み ---

# フィリピン周辺グリッドポイント読み込み
grid_df <- read.csv("data/grid_points_admin3.csv")

# 粗くする時：　グリッド間隔（例：0.5度）
grid_size <- 0.1
# grid_dfに粗いグリッド座標を付与
grid_df_coarse <- grid_df %>%
  mutate(
    glat_coarse = floor(glat / grid_size) * grid_size,
    glon_coarse = floor(glon / grid_size) * grid_size
  ) %>%
  distinct(glat_coarse, glon_coarse)  # 重複除外
# 確認
head(grid_df_coarse)
grid_df = grid_df_coarse

# Cebu周辺だけ抽出
grid_df <- grid_df_coarse %>%
  filter(
    glat_coarse >= 8.5, glat_coarse <= 11,
    glon_coarse >= 123, glon_coarse <= 125.5
  )

# --- 2. 台風データ読み込み ---

# 台風の進路データ読み込み
track_data <- read.csv("parsed_typhoon_data.csv")
track_data <- track_data %>%
  mutate(
    storm_id = paste0(STORMNAME, "_", substr(as.character(YYYYMMDDHH), 1, 4))
  )

# フィリピン周辺のデータだけ抽出
philippines_df <- track_data %>%
  filter(
    LAT >= 5, LAT <= 20,  # 緯度5～20度
    LON >= 115, LON <= 130,  # 経度115～130度
    !is.na(VMAX),  # NA除去
    VMAX > 0,       # 0除去
    !is.na(STORMNAME),  # NA除去
  )
track_data = philippines_df
# CSVに保存
write.csv(philippines_df, "philippines_df.csv", row.names = FALSE)


# --- 2. 風速推計実行 ---
# --- ソースとなるコード ---
source("source_test1.R")

wind_grids_df <- get_grid_winds(
  typhoon_track = track_data,
  grid_df = grid_df,
  tint = 1.0)  # 補間間隔（時間）設定は基本６時間毎 tint = 6.0



# --- 3. 出力保存 ---
# CSVに保存
write.csv(wind_grids_df, "gridded_df.csv", row.names = FALSE)
print(head(wind_grids_df))




# 台風カウント用のカラム追加
wind_grids_df$count <- 0  # カウント用列を追加
full_track <- read.csv("_full_track.csv")
full_track_rounded <- full_track %>%
  mutate(
    glat_coarse = floor(tclat / grid_size) * grid_size,
    glon_coarse = floor(tclon / grid_size) * grid_size
  )
# それぞれのグリッドに対してカウントアップ
for (i in 1:nrow(full_track_rounded)) {
  lat_i <- full_track_rounded$glat_coarse[i]
  lon_i <- full_track_rounded$glon_coarse[i]
  idx <- which(wind_grids_df$glat == lat_i & wind_grids_df$glon == lon_i)
  if (length(idx) > 0) {
    wind_grids_df$count[idx] <- wind_grids_df$count[idx] + 1
  }
}

# 
# まずカウント列を初期化
wind_grids_df$count500km <- 0
# full_trackを読み込み
full_track <- read.csv("_full_track.csv")
# 距離計算用の関数（ハバーサイン公式）
degrees_to_radians <- function(degrees) degrees * pi / 180
latlon_to_km <- function(lat1, lon1, lat2, lon2, R = 6371) {
  phi1 <- degrees_to_radians(lat1)
  phi2 <- degrees_to_radians(lat2)
  dphi <- degrees_to_radians(lat2 - lat1)
  dlambda <- degrees_to_radians(lon2 - lon1)
  a <- sin(dphi / 2)^2 + cos(phi1) * cos(phi2) * sin(dlambda / 2)^2
  c <- 2 * asin(min(1, sqrt(a)))
  dist_km <- R * c
  return(dist_km)
}
# full_trackの各点に対して
for (i in 1:nrow(full_track)) {
  track_lat <- full_track$tclat[i]
  track_lon <- full_track$tclon[i]
  # 各グリッドとの距離を計算
  for (j in 1:nrow(wind_grids_df)) {
    grid_lat <- wind_grids_df$glat[j]
    grid_lon <- wind_grids_df$glon[j]
    dist_km <- latlon_to_km(track_lat, track_lon, grid_lat, grid_lon)
    # 500km以内ならカウント+1
    if (!is.na(dist_km) && dist_km <= 500) {
      wind_grids_df$count500km[j] <- wind_grids_df$count500km[j] + 1
    }
  }
}



# --- 4. various plotting---
library(ggplot2)
library(viridis)

ggplot(wind_grids_df, aes(x = glon, y = glat, fill = windspeed)) +
  geom_tile() +
  borders("world", colour = "black", fill = NA) +  # Input world map
  scale_fill_viridis_c() +
  coord_fixed(xlim = c(122, 126), ylim = c(8, 12)) +  # Focus on Cebu
  labs(title = "Max Wind Speed around Cebu",
       x = "Longitude", y = "Latitude", fill = "Wind Speed (m/s)")
  ggsave("_max_wind_heatmap1.png", width = 8, height = 6, dpi = 300)


ggplot(wind_grids_df, aes(x = glon, y = glat, fill = count)) +
  geom_tile() +
  borders("world", colour = "black", fill = NA) +
  scale_fill_viridis_c(option = "plasma") +
  coord_fixed(xlim = c(122, 126), ylim = c(8, 12)) +
  labs(title = "Typhoon Passage (Landfall) Count around Cebu",
       x = "Longitude", y = "Latitude", fill = "Passage Count")
  ggsave("_typhoon_passage_count.png", width = 8, height = 6, dpi = 300)

ggplot(wind_grids_df, aes(x = glon, y = glat, fill = count500km)) +
  geom_tile() +
  borders("world", colour = "black", fill = NA) +
  scale_fill_viridis_c(option = "plasma") +
  coord_fixed(xlim = c(122, 126), ylim = c(8, 12)) +
  labs(title = "Typhoon Impact Count (within 500km) around Cebu",
       x = "Longitude", y = "Latitude", fill = "Passage Count")
  ggsave("_typhoon_impact_500km_count.png", width = 8, height = 6, dpi = 300)

ggplot(wind_grids_df, aes(x = glon, y = glat, z = windspeed)) +
  stat_summary_2d(fun = mean, bins = 100) +  # 100×100
  scale_fill_viridis_c(option = "plasma") +
  coord_fixed() +
  labs(title = "Binned Wind Speed Map (Typhoon Haiyan)",
       x = "Longitude", y = "Latitude", fill = "Mean Wind Speed") +
  theme_minimal()
  ggsave("_max_wind_heatmap2.png", width = 8, height = 6, dpi = 300)



png(filename = "_wind_vmax_point_map.png", width = 1200, height = 900)
colorscale <- colorRampPalette(c("blue", "green", "yellow", "red"))(100)
# VMAX正規化して色割り当て
vmax_norm <- (wind_grids_df$windspeed - min(wind_grids_df$windspeed, na.rm = TRUE)) / 
             (max(wind_grids_df$windspeed, na.rm = TRUE) - min(wind_grids_df$windspeed, na.rm = TRUE))
vmax_color_idx <- as.integer(vmax_norm * 99) + 1
# カラーバー
library(fields)
# 普通にplot
par(mar = c(5, 4, 4, 5))  # 標準的なマージン
plot(wind_grids_df$glon, wind_grids_df$glat,
     col = colorscale[vmax_color_idx],
     pch = 20, cex = 0.5,
     xlab = "Longitude", ylab = "Latitude",
     main = "Wind Speed colored by VMAX")
# カラーバーだけ別に右端に小さく表示
image.plot(legend.only = TRUE, 
           zlim = range(wind_grids_df$windspeed, na.rm = TRUE),
           col = colorscale,
           legend.lab = "VMAX (kt)",
           smallplot = c(0.92-0.04, 0.96-0.04, 0.2, 0.8))  # ←これで右端に固定！！  
dev.off()