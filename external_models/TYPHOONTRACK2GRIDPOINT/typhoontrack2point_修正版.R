## this model will calculate maximum wind speed and duration of maximum wind speeds for each grid location based on typhoon track data 
# typhoon Track data(For example PAGASA forecast comes with the follwoing information into gridpoint ,  
#VMAX is wind speed in Kt
#BASIN,CY,YYYYMMDDHH,LAT,LON,VMAX,STORMNAME
#WP,,201311040000,6.1,152.2,35,HAIYAN
#WP,,201311040600,6.2,150.4,35,HAIYAN
#WP,,201311041200,6.3,148.8,40,HAIYAN
#WP,,201311041800,6.5,147.2,45,HAIYAN
#WP,,201311050000,6.5,145.9,55,HAIYAN
#WP,,201311050600,6.5,144.6,60,HAIYAN
#WP,,201311051200,6.9,142.9,65,HAIYAN
#WP,,201311051800,7.1,141.3,75,HAIYAN
#WP,,201311060000,7.3,139.7,85,HAIYAN 

# But for typhoon model we need data at each grid location(manucipality centers) and 
# this coede is developed to calculate wind speed at any grid location in PRA, for 510
# typhoon model casse gridponts are manucipality population mean centers 

# this tool is based on the the work of Willoughby, HE, RWR Darling, and ME Rahn. 2006. 
# “Parametric Representation of the Primary Hurricane Vortex. Part II: A New Family of Sectionally Continuous Profiles.” 

library(ggplot2)
library(dplyr)
library(tidyr)
library(gridExtra)

# wind_track_haiyan  read data
TRACK_DATA <- read.csv("data/haiyan.csv")
grid_points <- read.csv("data/grid_points_admin3.csv", sep=";")

typhoon_names <- list('Bopha','Goni','Hagupit','Haima','Haiyan','Kalmaegi','Koppu','Melor','Nock-Ten','Rammasun','Sarika','Utor')

typhoon_names<-tolower(typhoon_names)
#rjdt1<-rjdt[rjdt$cycloneName_x %in% typhoon_names, ]


#setwd("....")
#BASIN,CY,YYYYMMDDHH,TECHNUM,TECH,TAU,LatN/S,LonE/W,vmax,mslp,ty,RAD,WINDCODE,RAD1,RAD2,RAD3,RAD4,RADP,RRP,MRD,GUSTS,EYE,SUBREGION,MAXSEAS,INITITIALS,DIR,STORMNAME,DEPTH

#TRACK_DATA<-TRACK_DATA[tolower(TRACK_DATA$STORMNAME) %in% typhoon_names, ]



#best_track<-TRACK_DATA[TRACK_DATA$YEAR >2011,]

# grid_points_ <- grid_points %>%   # カラム名どおりなのでこの行は不要
  # mutate(#gridid =ADM4_PCODE,#substr(ADM4_PCODE, 3,11),
  #        glat = Lat, 
  #        glon = Lon) %>%
  # select(gridid, glat, glon) 


#select only variables needed
data <- TRACK_DATA %>%
  mutate(
    index                          = 1:nrow(TRACK_DATA),
    date                           = as.character(YYYYMMDDHH),#sprintf("%12s", YYYYMMDDHH),
    latitude                       = as.numeric(LAT),#as.numeric(LAT),#sprintf("%03d", LAT)#,#as.numeric(as.character(TRACK_DATA$LAT)),
    longitude                      = as.numeric(LON),#as.numeric(LON),# as.numeric(as.character(TRACK_DATA$LON)),
    wind                           = as.numeric(VMAX),#*0.514444,#as.numeric(VMAX),# as.numeric(as.character(TRACK_DATA$VMAX)),
    typhoon_name                   = tolower(STORMNAME)
  ) %>%
  select (index                                   ,
          date                                    ,
          latitude                                ,
          longitude                               ,
          typhoon_name                            ,
          wind      )

radians_to_degrees<- function(radians){
  degrees  <-  radians *180/pi
  return(degrees)
}

degrees_to_radians<- function(degrees){
  radians <- degrees * pi / 180
  return(radians)
}

create_full_track <- function(typhoon_track, tint = 0.5){  
  
  typhoon_track <- typhoon_track %>%
    mutate(
      index                          = 1:nrow(typhoon_track),
      date                           = lubridate::ymd_hm(YYYYMMDDHH),
      tclat                           = abs(as.numeric(LAT)),
      tclon                           = as.numeric(LON),
      tclon                           = ifelse(tclon < 180, tclon, tclon - 180),
      latitude                       = as.numeric(LAT),#as.numeric(LAT),#sprintf("%03d", LAT)#,#as.numeric(as.character(TRACK_DATA$LAT)),
      longitude                      = as.numeric(LON),#as.numeric(LON),# as.numeric(as.character(TRACK_DATA$LON)),
      vmax                           = as.numeric(VMAX)*0.514444,#as.numeric(VMAX),# as.numeric(as.character(TRACK_DATA$VMAX)),
      typhoon_name                   = tolower(STORMNAME),
      wind                           = as.numeric(VMAX)*0.514444
    ) %>%
    select (date                                    ,
            latitude                                ,
            tclat                                   ,
            tclon                                   ,
            longitude                               ,
            typhoon_name                            ,
            wind                                    ,
            vmax      ) 
  
  interp_df <- floor(nrow(typhoon_track) / 3)-1
  #interp_df<- 30    
  interp_date <- seq(from = min(typhoon_track$date),
                     to = max(typhoon_track$date),
                     by = tint * 3600) # Date time sequence must use `by` in
  # seconds
  interp_date <- data.frame(date = interp_date)
  
  tclat_spline <- stats::glm(tclat ~ splines::ns(date, df = interp_df),  data = typhoon_track)
  interp_tclat <- stats::predict.glm(tclat_spline, newdata = interp_date)  
  tclon_spline <- stats::glm(tclon ~ splines::ns(date, df = interp_df),  data = typhoon_track)
  interp_tclon <- stats::predict.glm(tclon_spline, newdata = interp_date)
  
  vmax_spline <- stats::glm(vmax ~ splines::ns(date, df = interp_df),    data = typhoon_track)
  interp_vmax <- stats::predict.glm(vmax_spline, newdata = interp_date)
  
  full_track <- data.frame(date = interp_date, tclat = interp_tclat, tclon = interp_tclon, vmax = interp_vmax)
  return(full_track)
}



latlon_to_km<- function(lat1, lon1, lat2, lon2, Rearth = 6378.14){
  lat_1 <- degrees_to_radians(lat1)
  lon_1 <- degrees_to_radians(lon1)
  lat_2 <- degrees_to_radians(lat2)
  lon_2 <- degrees_to_radians(lon2)
  
  delta_L <- lon_1 - lon_2
  delta_tclat <- lat_1 - lat_2
  
  hav_L <- sin(delta_L / 2) ^ 2
  hav_tclat <- sin(delta_tclat / 2) ^ 2
  
  hav_gamma <- hav_tclat + cos(lat_1) * cos(lat_2) * hav_L
  gamma <- 2 * asin(sqrt(hav_gamma))
  
  dist <- Rearth * gamma
  return(dist)
}

calc_forward_speed<- function(lat_1, lon_1, time_1, lat_2, lon_2, time_2){
  dist <- latlon_to_km(lat_1, lon_1, lat_2, lon_2) * 1000
  time <- as.numeric(difftime(time_2, time_1, units = "secs"))
  typhoon_speed <- dist / time
  return(typhoon_speed)
}

##Calculate the direction of gradient winds at each location

calc_bearing<- function(lat_1, lon_1, lat_2, lon_2){
  lat_1 <- degrees_to_radians(lat_1)
  lon_1 <- degrees_to_radians(lon_1)
  lat_2 <- degrees_to_radians(lat_2)
  lon_2 <- degrees_to_radians(lon_2)
     
  S <- cos(lat_2) * sin(lon_1 - lon_2)
  C <- cos(lat_1) * sin(lat_2) - sin(lat_1) * cos(lat_2) * cos(lon_1 - lon_2)
  
  theta_rad <- atan2(S, C)
  theta <- radians_to_degrees(theta_rad) + 90
  theta <- theta %% 360 # restrict to be between 0 and 360 degrees
  return(theta)
}

remove_forward_speed<- function(vmax, tcspd){
  vmax_sfc_sym <- vmax - 0.5 * tcspd
  vmax_sfc_sym[vmax_sfc_sym < 0] <- 0
  return(vmax_sfc_sym)
}

calc_gradient_speed<- function(vmax_sfc_sym, over_land){
  reduction_factor <- 0.9
  if(over_land){
    reduction_factor <- reduction_factor * 0.8
  }
  vmax_gl <- vmax_sfc_sym / reduction_factor
  return(vmax_gl)
}

## to define land vs water locations in PAR area 

landmask <- readr::read_csv("data/landseamask_ph1.csv",
                            col_names = c("longitude", "latitude", "land")) %>%
  dplyr::mutate(land = factor(land, levels = c(1, 0), labels = c("land", "water")))


check_over_land<- function(tclat, tclon){
  lat_diffs <- abs(tclat - landmask$latitude)
  closest_grid_lat <- landmask$latitude[which(lat_diffs ==
                                                min(lat_diffs))][1]
  
  lon_diffs <- abs(tclon - (360 - landmask$longitude))
  closest_grid_lon <- landmask$longitude[which(lon_diffs ==
                                                 min(lon_diffs))][1]
  
  over_land <- landmask %>%
    dplyr::filter_(~ latitude == closest_grid_lat &
                     longitude == closest_grid_lon) %>%
    dplyr::mutate_(land = ~ land == "land") %>%
    dplyr::select_(~ land)
  over_land <- as.vector(over_land$land[1])
  
  return(over_land)
}


#Rmax: Radius from the storm center to the point at which the maximum wind occurs (km) this is based

will7a<- function(vmax_gl, tclat){
  Rmax <- 46.4 * exp(-0.0155 * vmax_gl + 0.0169 * tclat)
  return(Rmax)
}

# X1, which is a parameter needed for the Willoughby model. This is done using equation 10a from Willoughby et al. (2006):
# X1=317.1â2.026Vmax,G+1.915Ï

will10a<-function(vmax_gl, tclat){
  X1 <- 317.1 - 2.026 * vmax_gl + 1.915 * tclat
  return(X1)
}
#
#Next, the code calculates another Willoughby parameter, n. This is done with equation 10b from Willoughby et al. (2006):
#

will10b<- function(vmax_gl, tclat){
  n <- 0.4067 + 0.0144 * vmax_gl - 0.0038 * tclat
  return(n)
}
#Next, the code calculates another Willoughby parameter, A, with equation 10c from Willoughby et al. (2006)
will10c<- function(vmax_gl, tclat){
  A <- 0.0696 + 0.0049 * vmax_gl - 0.0064 * tclat
  A[A < 0 & !is.na(A)] <- 0
  return(A)
}

will3_right<- function(n, A, X1, Rmax){
  eq3_right <- (n * ((1 - A) * X1 + 25 * A)) /
    (n * ((1 - A) * X1 + 25 * A) + Rmax)
  return(eq3_right)
}


will3_deriv_func<- function(xi, eq3_right){
  deriv <- 70 * 9 * xi ^ 8 - 315 * 8 * xi ^ 7 + 540 * 7 * xi ^ 6 -
    420 * 6 * xi ^ 5 + 126 * 5 * xi ^ 4
  func <- 70 * xi ^ 9 - 315 * xi ^ 8 + 540 * xi ^ 7 - 420 * xi ^ 6 +
    126 * xi ^ 5 - eq3_right
  deriv_func <-c(deriv, func)
  return(deriv_func)
}

solve_for_xi<- function(xi0 = 0.5, eq3_right, eps = 10e-4, itmax = 100){
  if(is.na(eq3_right)){
    return(NA)
  } else{
    i <- 1
    xi <- xi0
    while(i <= itmax){
      deriv_func <- will3_deriv_func(xi, eq3_right)
      if(abs(deriv_func[2]) <= eps){ break }
      xi <- xi - deriv_func[2] / deriv_func[1]
    }
    if(i < itmax){
      return(xi)
    } else{
      warning("Newton-Raphson did not converge.")
      return(NA)
    }
  }
}


##While the Newton-Raphson method can sometimes perform poorly in finding global maxima, in this case the function for which we are trying ##to find the root is well-behaved. Across tropical storms from 1988 to 2015, the method never failed to converge, and identified roots ##were consistent across storms (typically roots are for Î¾ of 0.6--0.65). We also tested using the optim function in the stats R package ##and found similar estimated roots but slower convergence times than when using the Newton-Raphson method.

##Now an equation from the Willoughby et al. 2006 paper can be used to calculate R1 (Willoughby, Darling, and Rahn 2006):


calc_R1<- function(Rmax, xi){
  R2_minus_R1 <- ifelse(Rmax > 20, 25, 15)
  R1 <- Rmax - xi * R2_minus_R1
  return(R1)
}


##Determine radius for end of transition region
##Next, the code estimates the radius for the end of the transition period, R2. We assume that smaller storms (Rmaxââ¤â20 km) have a ##transition region of 15 km while larger storms (Rmaxâ>â20 km) have a transition region of 25 km:

##$$ R_2 = \begin{cases} R_1 + 25 & \text{ if } R_{max} > 20\mbox{ km}\\ R_1 + 15 & \text{ if } R_{max} \le 20\mbox{ km} \end{cases} $$

##where:

##R1: Radius to the start of the transition region (km)
##R2: Radius to the end of the transition region (km)
##R2 = ifelse(Rmax > 20, R1 + 25, R1 + 15)
##Calculate wind speed at each grid point
##Next, the code models the wind speed at a location (e.g., a Manucipality center).
#As a note, this function calculates wind characteristics at a 
#single location; a later function applies this function across many grid points):

##After calculating the grid wind time series for a grid point, 
#you can input the time series for a grid point into summarize_grid_wind to
##generate overall storm summaries for the grid point. 
#This functions calculate wind characteristics at each grid point (or Manucipality center #
# for every storm observation. These characteristics are:

##vmax_gust: Maximum value of surface-level (10 meters) sustained winds, m/s, over the length of the storm at the given ##location
##vmax_sust: Maximum value of surface-level (10 meters) gust winds, in m/s, over the length of the storm at the given location
##gust_dur: Length of time, in minutes, that surface-level sustained winds were above a certain wind speed cutoff
#(e.g., 20 meters per ##second)
##sust_dur: Length of time, in minutes, that surface-level gust winds were above a certain wind speed cutoff
#(e.g., 20 meters per second)

##Determine gradient wind speed at each location
##Next, the package calculates VG(r), the gradient level 1-minute sustained wind at the grid point, which is at radius r from the tropical ##cyclone center (Cdis**t for the grid point). Note there are different equations for VG(r) for (1) the eye to the start of the transition ##region; (2) outside the transition region; and (3) within the transition region.


will1<- function(cdist, Rmax, R1, R2, vmax_gl, n, A, X1, X2 = 25){
  
  if(is.na(Rmax) || is.na(vmax_gl) ||
     is.na(n) || is.na(A) || is.na(X1)){
    return(NA)
  } else {
    
    Vi <- vmax_gl * (cdist / Rmax) ^ n
    Vo <- vmax_gl * ((1 - A) * exp((Rmax - cdist)/X1) + A * exp((Rmax - cdist) / X2))
    
    if(cdist < R1){
      wind_gl_aa <- Vi
    } else if (cdist > R2){
      wind_gl_aa <- Vo
    } else {
      eps <- (cdist - R1) / (R2 - R1)
      w <- 126 * eps ^ 5 - 420 * eps ^ 6 + 540 * eps ^ 7 - 315 *
        eps ^ 8 + 70 * eps ^ 9
      wind_gl_aa <- Vi * (1 - w) + Vo * w
    }
    
    wind_gl_aa[wind_gl_aa < 0 & !is.na(wind_gl_aa)] <- 0
    
    return(wind_gl_aa)
  }
}

##Estimate surface level winds from gradient winds

gradient_to_surface<- function(wind_gl_aa, cdist){
  if(cdist <= 100){
    reduction_factor <- 0.9
  } else if(cdist >= 700){
    reduction_factor <- 0.75
  } else {
    reduction_factor <- 0.90 - (cdist - 100) * (0.15/ 600)
  }
  # Since all manucipalities are over land, reduction factor should
  # be 20% lower than if it were over water
  reduction_factor <- reduction_factor * 0.8
  wind_sfc_sym <- wind_gl_aa * reduction_factor
  return(wind_sfc_sym)
}

##Next, the function calculates the gradient wind direction based on the bearing of a location from the storm. 
#This gradient wind direction is##calculated by adding 90 degrees to the bearing of the grid point from the storm center.

#gwd = (90 + chead) %% 360

##Calculate the surface wind direction
##The next step is to change from the gradient wind direction to the surface wind direction. To do this, the function adds an inflow angle ##to the gradient wind direction (making sure the final answer is between 0 and 360 degrees). This step is necessary because surface ##friction changes the wind direction near the surface compared to higher above the surface.

##The inflow angle is calculated as 

add_inflow<- function(gwd, cdist, Rmax){
  if(is.na(gwd) | is.na(cdist) | is.na(Rmax)){
    return(NA)
  }
  
  # Calculate inflow angle over water based on radius of location from storm
  # center in comparison to radius of maximum winds (Phadke et al. 2003)
  if(cdist < Rmax){
    inflow_angle <- 10 + (1 + (cdist / Rmax))
  } else if(Rmax <= cdist & cdist < 1.2 * Rmax){
    inflow_angle <- 20 + 25 * ((cdist / Rmax) - 1)
  } else {
    inflow_angle <- 25
  }
  
  # Add 20 degrees to inflow angle since location is over land, not water
  overland_inflow_angle <- inflow_angle + 20
  
  # Add inflow angle to gradient wind direction
  gwd_with_inflow <- (gwd + overland_inflow_angle) %% 360
  
  return(gwd_with_inflow)
}

#Add back in wind component from forward speed of storm Next, to add back in the storm's forward motion at each grid point, the code #reverses the earlier step that used the Phadke correction factor (equation 12, Phadke et al. 2003). The package calculates a constant #correction factor (correction_factor), as a function of r, radius from the storm center to the grid point, and Rmax, radius from storm #center to maximum winds.

#$$ U(r) = \frac{R_{max}r}{R_{max}^2 + r^2}F $$ where:


add_forward_speed <- function(wind_sfc_sym, tcspd_u, tcspd_v, swd, cdist, Rmax){
  # Calculate u- and v-components of surface wind speed
  swd<- swd * pi / 180
  wind_sfc_sym_u <- wind_sfc_sym * cos(swd)
  wind_sfc_sym_v <-  wind_sfc_sym * sin(swd)
  
  # Add back in component from forward motion of the storm
  correction_factor <- (Rmax * cdist) / (Rmax ^ 2 + cdist ^ 2)
  
  # Add tangential and forward speed components and calculate
  # magnitude of this total wind
  wind_sfc_u <- wind_sfc_sym_u + correction_factor * tcspd_u
  wind_sfc_v <- wind_sfc_sym_v + correction_factor * tcspd_v
  wind_sfc <- sqrt(wind_sfc_u ^ 2 + wind_sfc_v ^ 2)
  
  # Reset any negative values to 0
  wind_sfc <- ifelse(wind_sfc > 0, wind_sfc, 0)
  
  return(wind_sfc)
}


#Calculate 3-second gust wind speed from sustained wind speed

#Here is a table with gust factors based on location (Harper, Kepert, and Ginger 2010):

#Location	Gust factor 
#In-land	1.49
#Just offshore	1.36
#Just onshore	1.23
#At sea	1.11
#The stormwindmodel package uses the "in-land" gust factor value throughout.

# windspeed: track_dataのデータと仮定して　added by KK
windspeed <- data$wind

gustspeed = windspeed * 1.49

get_grid_winds<- function(typhoon_track, grid_df ,tint = 0.5,gust_duration_cut = 20,sust_duration_cut = 40){
  full_track <- create_full_track(typhoon_track = TRACK_DATA, tint = tint)
  with_wind_radii <- add_wind_radii(full_track = full_track)
  
  grid_winds <- plyr::adply(grid_df, 1, calc_and_summarize_grid_wind,
                            with_wind_radii = with_wind_radii,
                            tint = tint,
                            gust_duration_cut = gust_duration_cut,
                            sust_duration_cut = sust_duration_cut)
  
  return(grid_winds)
}



add_wind_radii <-function(full_track = create_full_track()){
  
  with_wind_radii <- full_track %>%
    dplyr::mutate_(tcspd = ~ calc_forward_speed(tclat, tclon, date,
                                                dplyr::lead(tclat),
                                                dplyr::lead(tclon),
                                                dplyr::lead(date)),
                   tcdir = ~ calc_bearing(tclat, tclon,
                                          dplyr::lead(tclat),
                                          dplyr::lead(tclon)),
                   tcspd_u = ~ tcspd * cos(tcdir* pi / 180),
                   tcspd_v = ~ tcspd * sin(tcdir* pi / 180),
                   vmax_sfc_sym = ~ remove_forward_speed(vmax, tcspd),
                   over_land = ~ mapply(check_over_land, tclat, tclon),
                   vmax_gl = ~ mapply(calc_gradient_speed,
                                      vmax_sfc_sym = vmax_sfc_sym,
                                      over_land = over_land),
                   Rmax = ~ will7a(vmax_gl, tclat),
                   X1 = ~ will10a(vmax_gl, tclat),
                   n = ~ will10b(vmax_gl, tclat),
                   A = ~ will10c(vmax_gl, tclat),
                   eq3_right = ~ will3_right(n, A, X1, Rmax),
                   xi = ~ mapply(solve_for_xi, eq3_right = eq3_right),
                   R1 = ~ calc_R1(Rmax, xi),
                   R2 = ~ ifelse(Rmax > 20, R1 + 25, R1 + 15)
    ) %>%
    dplyr::select_(quote(-vmax), quote(-tcspd), quote(-vmax_sfc_sym),
                   quote(-over_land), quote(-eq3_right), quote(-xi))
  return(with_wind_radii)
}

calc_grid_wind <- function(grid_points,
                           with_wind_radii = add_wind_radii()){
  print(head(grid_points))
  
  grid_wind <- dplyr::mutate_(with_wind_radii,
                              # Calculated distance from storm center to location
                              cdist = ~ latlon_to_km(tclat, tclon,
                                                     grid_points$glat, grid_points$glon),
                              # Calculate gradient winds at the point
                              wind_gl_aa = ~ mapply(will1, cdist = cdist, Rmax = Rmax,
                                                    R1 = R1, R2 = R2, vmax_gl = vmax_gl,
                                                    n = n, A = A, X1 = X1),
                              # calculate the gradient wind direction (gwd) at this
                              # grid point
                              chead = ~ calc_bearing(tclat, tclon,
                                                     grid_points$glat, - grid_points$glon),
                              gwd = ~ (90 + chead) %% 360,
                              # Bring back to surface level (surface wind reduction factor)
                              wind_sfc_sym = ~ mapply(gradient_to_surface,
                                                      wind_gl_aa = wind_gl_aa,
                                                      cdist = cdist),
                              # Get surface wind direction
                              swd = ~ mapply(add_inflow, gwd = gwd, cdist = cdist,
                                             Rmax = Rmax),
                              # Add back in storm forward motion component
                              windspeed = ~ add_forward_speed(wind_sfc_sym,
                                                              tcspd_u, tcspd_v,
                                                              swd, cdist, Rmax)) %>%
    dplyr::select_(~ date, ~ windspeed)
  return(grid_wind)
}

get_grid_winds <- function(typhoon_track,
                           grid_df,
                           tint = 0.5,
                           gust_duration_cut = 20,
                           sust_duration_cut = 40){
  full_track <- create_full_track(typhoon_track = TRACK_DATA, tint = tint)
  with_wind_radii <- add_wind_radii(full_track = full_track)
  
  grid_winds <- plyr::adply(grid_df, 1, calc_and_summarize_grid_wind,
                            with_wind_radii = with_wind_radii,
                            tint = tint,
                            gust_duration_cut = gust_duration_cut,
                            sust_duration_cut = sust_duration_cut)
  
  return(grid_winds)
}


summarize_grid_wind <- function(grid_wind, tint = 0.5, gust_duration_cut = 20,
                                sust_duration_cut = 20){
  grid_wind_summary <- grid_wind %>%
    dplyr::mutate_(gustspeed = ~ windspeed * 1.49) %>%
    # Determine max of windspeed and duration of wind over 20
    dplyr::summarize_(vmax_gust = ~ max(gustspeed, na.rm = TRUE),
                      vmax_sust = ~ max(windspeed, na.rm = TRUE),
                      gust_dur = ~ 60 * sum(gustspeed > gust_duration_cut,
                                            na.rm = TRUE),
                      sust_dur = ~ 60 * sum(windspeed > sust_duration_cut,
                                            na.rm = TRUE)) %>%
    dplyr::mutate_(gust_dur = ~ gust_dur * tint,
                   sust_dur = ~ sust_dur * tint)
  grid_wind_summary <- as.matrix(grid_wind_summary)
  return(grid_wind_summary)
}

calc_and_summarize_grid_wind <- function(grid_points,
                                         with_wind_radii = add_wind_radii(),
                                         tint = 0.5, gust_duration_cut = 20,
                                         sust_duration_cut = 20){
  grid_wind <- calc_grid_wind(grid_points = grid_points,
                              with_wind_radii = with_wind_radii)
  grid_wind_summary <- summarize_grid_wind(grid_wind = grid_wind, tint = tint,
                                           gust_duration_cut = gust_duration_cut,
                                           sust_duration_cut = sust_duration_cut)
  return(grid_wind_summary)
  
}

#### example to calculate typhoon data for each Manucipality 


# then calculate 
print(head(grid_points))
print(head(TRACK_DATA))
wind_grids <- get_grid_winds(typhoon_track=TRACK_DATA, grid_df=grid_points,tint = 0.5,gust_duration_cut = 40,sust_duration_cut = 20)
#typhoon_track=TRACK_DATA, grid_df=grid_points_,tint = 0.5,gust_duration_cut = 40,sust_duration_cut = 20)

# the result will be maximum sustained wind, gust and duration for sustianed wind and gust 
	
#gridid glat glonb bvmax_gust vmax_sust gust_dur sust_dur
#PH175312018 11.071 119.386 33.380596 22.403085 1200 480
#PH175312018 11.071 119.386 33.380596 22.403085 1200 480
#PH175312018 11.076 119.391  33.231415 22.302963  1200  450
#PH175312018 11.076 119.385 33.295912 22.346250 1200 450 
#PH175312018 11.087 119.398 32.951383 22.115022  1200 450


#referances
# stormwindmodel 
# Harper, BA, JD Kepert, and JD Ginger. 2010. “Guidelines for Converting Between Various Wind Averaging Periods in Tropical Cyclone Conditions.” World Meteorological Organization, WMO/TD 1555.
# Jones, Owen, Robert Maillardet, and Andrew Robinson. 2009. Introduction to Scientific Programming and Simulation Using R. Boca Raton, FL: Chapman & Hall/CRC Press.
# Knaff, John A, Mark DeMaria, Debra A Molenar, Charles R Sampson, and Matthew G Seybold. 2011. “An Automated, Objective, Multiple-Satellite-Platform Tropical Cyclone Surface Wind Analysis.” Journal of Applied Meteorology and Climatology 50 (10): 2149–66.
# Phadke, Amal C, Christopher D Martino, Kwok Fai Cheung, and Samuel H Houston. 2003. “Modeling of Tropical Cyclone Winds and Waves for Emergency Management.” Ocean Engineering 30 (4): 553–78.
# Press, William H, Saul A Teukolsky, William T Vetterling, and Brian P Flannery. 2002. Numerical Recipes in C++: The Art of Scientific Computing. 2nd ed. Cambridge, UK: Cambridge University Press.
# Willoughby, HE, RWR Darling, and ME Rahn. 2006. “Parametric Representation of the Primary Hurricane Vortex. Part II: A New Family of Sectionally Continuous Profiles.” Monthly Weather Review 134 (4): 1102–20.
