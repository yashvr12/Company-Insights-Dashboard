from flask import Flask, render_template, request
import pandas as pd
import plotly.express as px
import numpy as np

data = pd.read_csv(r"cleaned_data.csv", index_col=0)


app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    industry = [i for i in data["industry"].unique() if type(i) == str]
    industry.sort()

    location = [i for i in data["location"].unique() if type(i) == str]
    location.sort()
    return render_template("index.html", industry=industry, location=location)

@app.route("/search", methods=["GET"])
def search():
    filtered_data = data.copy()

    company = request.args.get("company")
    if company and not filtered_data.empty:
        filtered_data = filtered_data[filtered_data["company_name"].apply(lambda x: company in x.lower())]

    location = request.args.get("location")
    if location and not filtered_data.empty:
        filtered_data = filtered_data[filtered_data["location"] == location]

    rating = request.args.get("rating")
    if rating and not filtered_data.empty:
        filtered_data = filtered_data[filtered_data["company_rating"] >= int(rating)]

    industry = request.args.get("industry")
    if industry and not filtered_data.empty:
        filtered_data = filtered_data[filtered_data["industry"] == industry]

    sortby = request.args.get("sortby")
    if sortby and not filtered_data.empty:
        isAsc = sortby[0] == "a"
        filtered_data = filtered_data.sort_values(sortby[2:], ascending=isAsc)

    page = request.args.get("page")
    if page:
        page = int(page)
    else:
        page = 0

    plots = []

    # Company ratings
    rating_data = filtered_data["company_rating"].value_counts().sort_index().reset_index()
    rating_data.columns = ["company_rating", "company_count"]

    fig = px.area(rating_data, x="company_rating", y="company_count")
    fig.update_layout(title="Company Ratings Distribution", xaxis_title="Rating", yaxis_title="Count")
    plots.append(fig.to_html(full_html=False, include_plotlyjs="cdn"))

    # Company size
    size_data = filtered_data["size"].apply(lambda x: round(np.array(list(map(int, "".join(x.split("+")).split("-")))).mean()) if type(x) == str else np.nan).value_counts().sort_index().reset_index()
    size_data.columns = ["company_size", "count"]

    fig = px.area(size_data, x="company_size", y="count")
    fig.update_layout(title="Company Size Distribution", xaxis_title="Size (in employees)", yaxis_title="Count")
    plots.append(fig.to_html(full_html=False, include_plotlyjs="cdn"))

    # Company age
    age_data = filtered_data["years_old"].value_counts().sort_index().reset_index()
    age_data.columns = ["company_age", "company_count"]
    fig = px.area(age_data, x="company_age", y="company_count")
    fig.update_layout(title="Company Age Distribution", xaxis_title="Company age", yaxis_title="Count")
    plots.append(fig.to_html(full_html=False, include_plotlyjs="cdn"))

    # Best companies
    normalized_rating = (filtered_data["company_rating"] / filtered_data["company_rating"].max()).fillna(0.3)
    temp = filtered_data["size"].apply(lambda x: round(np.array(list(map(int, "".join(x.split("+")).split("-")))).mean()) if type(x) == str else np.nan)
    normalized_size = (temp / temp.max()).fillna(0.3)
    normalized_age = (filtered_data["years_old"] / filtered_data["years_old"].max()).fillna(0.3)
    
    filtered_data["best_value"] = (normalized_rating + normalized_size + normalized_age) / 3
    best_companies = filtered_data.drop_duplicates(ignore_index=True, subset=["company_name", "company_rating", "best_value"]).sort_values("best_value", ascending=False).head(25)
    
    fig = px.bar(best_companies, x="company_name", y="best_value", color="industry")
    fig.update_layout(title="Best Companies by Rating, Size, and Age", xaxis_title="Company Name", yaxis_title="Best Value")
    plots.append(fig.to_html(full_html=False, include_plotlyjs="cdn"))

    # Average rating by industry
    rated_industry = filtered_data.groupby("industry")["company_rating"].mean().sort_values(ascending=False).reset_index()
    rated_industry.columns = ["industry", "company_rating"]
    rated_industry["industry"] = rated_industry["industry"].apply(lambda x: x[:30] + "..." if type(x) == str and len(x) > 30 else x)

    fig = px.bar(rated_industry, x="industry", y="company_rating")
    fig.update_layout(title="Average rating by Industry", xaxis_title="Industry", yaxis_title="Rating")
    plots.append(fig.to_html(full_html=False, include_plotlyjs="cdn"))

    # Company count by industry
    industry_data = filtered_data["industry"].dropna().apply(lambda x: x[:30] + "..." if len(x) > 30 else x).value_counts().reset_index()
    industry_data.columns = ["industry", "company_count"]
    fig = px.bar(industry_data, x="industry", y="company_count")
    fig.update_layout(title="Company count by Industry", xaxis_title="Industry", yaxis_title="Count")
    plots.append(fig.to_html(full_html=False, include_plotlyjs="cdn"))

    # Company count by location
    temp = filtered_data["location"].value_counts(normalize=True)
    location_data = filtered_data["location"].apply(lambda x: x if temp[x] > 0.05 else "Other Locations").value_counts().reset_index()
    location_data.columns = ["location", "company_count"]

    fig = px.pie(location_data, values="company_count", names="location")
    fig.update_layout(title="Company count by Location")
    plots.append(fig.to_html(full_html=False, include_plotlyjs="cdn"))

    # Relation between rating and age
    relation = filtered_data.copy()
    relation["industry"] = relation["industry"].apply(lambda x: x[:30] + "..." if type(x) == str and len(x) > 30 else x)
    fig = px.scatter(relation, x="years_old", y="company_rating", hover_name="company_name", color="industry")
    fig.update_layout(title="Relation between Rating and Company Age", xaxis_title="Company Age", yaxis_title="Rating")
    plots.append(fig.to_html(full_html=False, include_plotlyjs="cdn"))

    filtered_data.drop(columns=["best_value"], inplace=True)
    
    return render_template("search.html", 
                           data=filtered_data[page * 50 : (page * 50) + 50].to_dict(orient="records"), 
                           total_results=len(filtered_data), 
                           page=page,
                           plots=plots,
    ) 


if __name__ == "__main__":
    app.run(host="0.0.0.0",port=12345,debug=True)