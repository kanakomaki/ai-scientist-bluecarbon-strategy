# --- directory settings ---
args <- commandArgs(trailingOnly = TRUE)
out_dir <- "."

# search "--out_dir=..."
for (arg in args) {
  if (grepl("^--out_dir=", arg)) {
    out_dir <- sub("^--out_dir=", "", arg)
  }
}

if (!dir.exists(out_dir)) {
  dir.create(out_dir, recursive = TRUE)
}

# ---
library(dplyr)

# --- 1. load grid points & focus on Cebu area---

# load grid points
grid_df <- read.csv("inputs/grid_points_admin3.csv")

# coarse grid
grid_size <- 0.1
# coarse grid
grid_df_coarse <- grid_df %>%
  mutate(
    glat_coarse = floor(glat / grid_size) * grid_size,
    glon_coarse = floor(glon / grid_size) * grid_size
  ) %>%
  distinct(glat_coarse, glon_coarse)  # delete overlap 
head(grid_df_coarse)
grid_df = grid_df_coarse

# Cebu area
grid_df <- grid_df_coarse %>%
  filter(
    glat_coarse >= 8.5, glat_coarse <= 11,
    glon_coarse >= 123, glon_coarse <= 125.5
  )

# --- 2. load typhoon data ---

# typhoon track data
track_data <- read.csv("inputs/parsed_typhoon_data.csv")
track_data <- track_data %>%
  mutate(
    storm_id = paste0(STORMNAME, "_", substr(as.character(YYYYMMDDHH), 1, 4))
  )

# clear cut for Philippines area
philippines_df <- track_data %>%
  filter(
    LAT >= 5, LAT <= 20,  # 
    LON >= 115, LON <= 130,  # 
    !is.na(VMAX),  # NA
    VMAX > 0,       # 0
    !is.na(STORMNAME),  # NA
  )
track_data = philippines_df
# CSV
# write.csv(philippines_df, "philippines_df.csv", row.names = FALSE)


# --- 2. predict wind speed decreasing---
# --- source code ---
source("src/source_functions.r")

wind_grids_df <- get_grid_winds(
  out_dir = out_dir,
  typhoon_track = track_data,
  grid_df = grid_df,
  tint = 1.0)  # temporal interpolation for 6 hours basically tint = 6.0



# --- save ---
# CSV
#write.csv(wind_grids_df, "gridded_df.csv", row.names = FALSE)
#print(head(wind_grids_df))




# ---- typhoon passage count ----
wind_grids_df$count <- 0  # col for typhoon passage count
full_track <- read.csv(file.path(out_dir,"_full_track.csv"))
full_track_rounded <- full_track %>%
  mutate(
    glat_coarse = floor(tclat / grid_size) * grid_size,
    glon_coarse = floor(tclon / grid_size) * grid_size
  )
# count up for each grid point
for (i in 1:nrow(full_track_rounded)) {
  lat_i <- full_track_rounded$glat_coarse[i]
  lon_i <- full_track_rounded$glon_coarse[i]
  idx <- which(wind_grids_df$glat == lat_i & wind_grids_df$glon == lon_i)
  if (length(idx) > 0) {
    wind_grids_df$count[idx] <- wind_grids_df$count[idx] + 1
  }
}

# 
# initializing the count500km column
wind_grids_df$count500km <- 0
# read the full track data
full_track <- read.csv(file.path(out_dir,"_full_track.csv"))
# function for distance calculation / 距離計算用の関数（ハバーサイン公式）
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
# for every point in full_track
for (i in 1:nrow(full_track)) {
  track_lat <- full_track$tclat[i]
  track_lon <- full_track$tclon[i]
  # distance calculation to every grid point
  for (j in 1:nrow(wind_grids_df)) {
    grid_lat <- wind_grids_df$glat[j]
    grid_lon <- wind_grids_df$glon[j]
    dist_km <- latlon_to_km(track_lat, track_lon, grid_lat, grid_lon)
    # if <500km count +1
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
  ggsave(file.path(out_dir,"max_wind_heatmap1.png"), width = 8, height = 6, dpi = 300)


ggplot(wind_grids_df, aes(x = glon, y = glat, fill = count)) +
  geom_tile() +
  borders("world", colour = "black", fill = NA) +
  scale_fill_viridis_c(option = "plasma") +
  coord_fixed(xlim = c(122, 126), ylim = c(8, 12)) +
  labs(title = "Typhoon Passage (Landfall) Count around Cebu",
       x = "Longitude", y = "Latitude", fill = "Passage Count")
  ggsave(file.path(out_dir,"typhoon_passage_count.png"), width = 8, height = 6, dpi = 300)

ggplot(wind_grids_df, aes(x = glon, y = glat, fill = count500km)) +
  geom_tile() +
  borders("world", colour = "black", fill = NA) +
  scale_fill_viridis_c(option = "plasma") +
  coord_fixed(xlim = c(122, 126), ylim = c(8, 12)) +
  labs(title = "Typhoon Impact Count (within 500km) around Cebu",
       x = "Longitude", y = "Latitude", fill = "Passage Count")
  ggsave(file.path(out_dir,"typhoon_impact_500km_count.png"), width = 8, height = 6, dpi = 300)
