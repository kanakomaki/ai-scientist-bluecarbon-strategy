# === typhoontrack2point_fixed.R ===

# 必要なライブラリ
library(dplyr)
library(readr)
library(lubridate)
library(splines)

# --- Helper functions ---
degrees_to_radians <- function(degrees) degrees * pi / 180
radians_to_degrees <- function(radians) radians * 180 / pi


# 緯度経度から距離(km)を計算する関数（ハバーサインの公式を使用）
latlon_to_km <- function(lat1, lon1, lat2, lon2, R = 6371) {
  # 引数の緯度経度をラジアンに変換
  phi1 <- lat1 * pi / 180
  phi2 <- lat2 * pi / 180
  dphi <- (lat2 - lat1) * pi / 180
  dlambda <- (lon2 - lon1) * pi / 180
  # ハバーサイン（haversine）公式による距離計算
  a <- sin(dphi / 2)^2 + cos(phi1) * cos(phi2) * sin(dlambda / 2)^2
  c <- 2 * asin(min(1, sqrt(a)))       # asinの引数が1を超えないようmin(1, ...)で調整
  dist_km <- R * c                 # 地球半径R（km）との積
  return(dist_km)
}

# 台風のベストトラック（経路）データを補間してフルのトラックを作成する関数
# tint: 補間間隔（時間単位、例：0.5 は30分間隔）
create_full_track <- function(.x, tint = 1.0) {
  # 1. 日付文字列を日時型に変換し、緯度・経度・風速を数値型にする
  #    元データのVMAXはkt（ノット）なので、m/sに変換する (1 kt = 0.514444 m/s)
  .x <- .x %>%
    dplyr::mutate(
      #date      = lubridate::ymd_hm(.data$YYYYMMDDHH),        # "YYYYMMDDHHMM"を日時型に変換
      date      = lubridate::ymd_h(.data$YYYYMMDDHH),        # "YYYYMMDDHHMM"を日時型に変換 ymd_h(YYYYMMDDHH)
      latitude  = as.numeric(.data$LAT),                      # 緯度を数値型に
      longitude = as.numeric(.data$LON),                      # 経度を数値型に
      vmax      = as.numeric(.data$VMAX) * 0.514444           # VMAXをm/sに変換
    ) %>%
    dplyr::arrange(date)                                      # 日付で並べ替え（昇順）
  
  # 補間対象が少なすぎる場合はそのまま使う
  if (nrow(.x) < 5) {
#  if (nrow(.x) < 4) {
    # message(paste0("Skipping interpolation for storm: ", .x$YYYYMMDDHH))
    return(.x %>%
      dplyr::transmute(
        #STORMNAME,
        date,
        tclat = latitude,
        tclon = longitude,
        vmax
      ))
  }
  
  # 2. 補間用の日時シーケンスを作成（tint間隔ごとに最小日時～最大日時まで）
  # message(paste0("Execute: interpolation: ", .x$YYYYMMDDHH))
  interp_times <- seq(from = min(.x$date),
                      to   = max(.x$date),
                      by   = tint * 3600)  # tint（時間）を秒に換算

  # 3. スプライン補間の自由度(df)を設定
  #    データ点数に応じたdf（おおよそデータ数/3）を使用し、最低でも1とする
  interp_df <- max(floor(nrow(.x) / 3) - 1, 1)

  # 4. 日付を説明変数として、緯度・経度・vmax（風速）をそれぞれスプライン補間
  lat_spline  <- stats::glm(latitude  ~ splines::ns(date, df = interp_df), data = .x)
  lon_spline  <- stats::glm(longitude ~ splines::ns(date, df = interp_df), data = .x)
  vmax_spline <- stats::glm(vmax      ~ splines::ns(date, df = interp_df), data = .x)

  # 新しい時間シーケンス上で予測（補間値）を計算
  # interp_data <- data.frame(date = interp_times)
  # lat_pred  <- stats::predict(lat_spline,  newdata = interp_data)
  # lon_pred  <- stats::predict(lon_spline,  newdata = interp_data)
  # vmax_pred <- stats::predict(vmax_spline, newdata = interp_data)
  interp_data <- data.frame(date = interp_times)
  lat_pred  <- predict(lat_spline,  newdata = interp_data)
  lon_pred  <- predict(lon_spline,  newdata = interp_data)
  vmax_pred <- pmax(predict(vmax_spline, newdata = interp_data), 0)  # 負値は0にする

  # 5. 補間後のvmaxが負になる場合は0に切り上げる（下限を0に揃える）
  vmax_pred[vmax_pred < 0] <- 0

  # 6. 補間結果のデータフレームを作成して返す
  full_track <- data.frame(
#    STORMNAME = .x$STORMNAME[1],  # <- 渡されたグループ（台風）から取る！
    #STORMNAME = rep(ifelse("STORMNAME" %in% names(.x), as.character(.x$STORMNAME[1]), NA), length(interp_times)),
    date      = interp_times,
    # latitude  = lat_pred,
    # longitude = lon_pred,
    tclat  = lat_pred,
    tclon = lon_pred,
    vmax      = vmax_pred
  )
  return(full_track)

}

# 与えられた台風トラックから各グリッド地点の最大風速を計算する関数
# 距離減衰モデルを適用し、各グリッドの風速を算出する
get_grid_winds <- function(typhoon_track, grid_df, tint = 1.0) {
  # 1. 台風経路データを補間してフルのトラックを取得（日時、緯度、経度、vmax[m/s]）
#  full_track <- create_full_track(typhoon_track, tint = tint)
  # 台風ごとにcreate_full_trackを個別に実行して、全部まとめる
  full_track <- typhoon_track %>%
#    group_by(STORMNAME) %>%
    group_by(storm_id) %>%
    group_modify(~ create_full_track(.x, tint = tint)) %>%
    ungroup()   # ←ここで必ずungroupしておく

  write.csv(full_track, "_full_track.csv", row.names = FALSE)
  message(paste0("Finished: full_tack"))
  
  # 2. 距離減衰モデルを定義する関数
  #    （例：50km以内=減衰なし、100kmで50%減衰、200kmで75%減衰、それ以上は90%減衰）
  decay_factor <- function(dist_km) {
    if (is.na(dist_km)) {
    return(NA)  # あるいはreturn(0)でもいい（どっちがいいかは設計による）
    }
    if (dist_km <= 50) {
      return(1.0)    # 50 km以内では風速そのまま（減衰率0%）
    } else if (dist_km <= 100) {
      return(0.50)   # 100 kmで風速50%に減衰
    } else if (dist_km <= 200) {
      return(0.25)   # 200 kmで風速25%に減衰
    } else {
      return(0.10)   # 200 km以上は風速10%まで減衰
    }
  }

  # 3. 各グリッド地点について、フルトラック上の各時刻の風速を計算し最大値を求める
  result_list <- list()  # 結果格納用リスト
  for (i in 1:nrow(grid_df)) {
    # グリッドの位置（緯度・経度）
    glat <- grid_df$glat[i]
    glon <- grid_df$glon[i]
    message(paste0("GRID: glat, glon = ", glat, ", ", glon, " (", i, "/", nrow(grid_df), ")"))

    # このグリッド地点における風速の最大値を初期化
    max_wind <- 0

    # フルトラックの各時点について風速を計算
    for (j in 1:nrow(full_track)) {
      # 台風位置（緯度・経度）とそのときのvmax
      track_lat  <- full_track$tclat[j]  # 中心位置だけのとき　・　台風からの距離があるときはtclat--> latitudeに修正する必要あり
      track_lon  <- full_track$tclon[j]
      track_wind <- full_track$vmax[j]        # 台風の最大風速 (m/s) at time j

      # グリッドと台風位置の距離を計算 (km)
      dist_km <- latlon_to_km(track_lat, track_lon, glat, glon)
      #message(paste0("dixt_km = ", dist_km, " km"))
      if (is.na(dist_km) || dist_km > 500) next  # 500km以上は無視

      # 距離減衰モデルを適用し、グリッド上の風速を計算
      wind_at_grid <- track_wind * decay_factor(dist_km)

      # 風速の最大値を更新
      if (!is.na(wind_at_grid) && !is.na(max_wind) && wind_at_grid > max_wind) {
        max_wind <- wind_at_grid
      }
    }

    # グリッド地点ごとの結果をデータフレームとして保存
    result_list[[i]] <- data.frame(glat = glat, glon = glon, windspeed = max_wind)
  }

  # リストを結合して結果のデータフレームを作成し返す
  result_df <- do.call(rbind, result_list)
  message(paste0("result_df FINISHED: ", nrow(result_df), " rows"))
  return(result_df)
}


