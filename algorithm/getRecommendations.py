from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

def get_recommendations(df, user_profile, top_n):
    df['Profile'] = df['Location'] + ' ' + df['Gender'] + ' ' + df['Age'].astype(str) + ' ' + \
                df['Habits'] + ' ' + df['FoodPreference'] + ' ' + df['Profession'] + ' ' + \
                df['Religion'] + ' ' + df['SleepSchedule'] + ' ' + df['CleanlinessHabits'] + ' ' + \
                df['PetFriendliness'] + ' ' + df['Adventurous'] + ' ' + df['Organized'] + ' ' + \
                df['Social'] + ' ' + df['Compromise'] + ' ' + df['Stress'] + ' ' + \
                df['Exploring'] + ' ' + df['Proactive'] + ' ' + df['Seekout'] + ' ' + \
                df['Patient'] + ' ' + df['Emotional']

    # train_data, _ = train_test_split(df, test_size=0.2, random_state=42)
    tfidf_vectorizer = TfidfVectorizer(stop_words='english')
    tfidf_matrix = tfidf_vectorizer.fit_transform(df['Profile'].values.astype('U'))
    user_profile_matrix = tfidf_vectorizer.transform([user_profile])
    # Filter the dataset based on the user's location
    location = (user_profile.split(':')[1].strip()).split(' ')[0]
    age = int((user_profile.split(':')[3].strip()).split(' ')[0])
    # Extracting location from user_profile
     
    filtered_df = df[df['Location'] == location]
    # filtered_df = df[df['Age'].astype(int) == age]
    filtered_df = filtered_df[(df['Age'].astype(int) >= (age - 4)) & (df['Age'].astype(int) <= (age + 4))]
    filtered_df = filtered_df[filtered_df['Listed'] == 0]
    
    if filtered_df.empty:
        return "No profiles found for the provided location."

    tfidf_matrix_filtered = tfidf_vectorizer.transform(filtered_df['Profile'].values.astype('U'))
    cosine_similarities = linear_kernel(user_profile_matrix, tfidf_matrix_filtered).flatten()

    gender_weight = 2
    Habits_Weight = 1.2
    FoodPreference_Weight = 1.2
    Religion_Weight = 1.2
    SleepSchedule_Weight = 1.2
    CleanlinessHabits_Weight = 1.2

    adjusted_similarity_scores = cosine_similarities * gender_weight * Habits_Weight * FoodPreference_Weight * Religion_Weight * SleepSchedule_Weight * CleanlinessHabits_Weight
    similar_profiles_indices = adjusted_similarity_scores.argsort()[::-1][1:top_n]
    match_percentage_scores = cosine_similarities[similar_profiles_indices] * 100

    recommendations = filtered_df.iloc[similar_profiles_indices][['Username']]
    recommendations['MatchPercentage'] = match_percentage_scores.round(0)
    recommendations['Age'] = filtered_df['Age']
    recommendations['Gender'] = filtered_df['Gender']

    return recommendations


